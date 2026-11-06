from flask import Flask,render_template,request,redirect,url_for,session,flash,abort
from werkzeug.security import check_password_hash
from functools import wraps
from datetime import datetime
from decimal import Decimal
from config import Config
from database.db import init_pool,fetch,execute,get_connection
app=Flask(__name__); app.config.from_object(Config)
def audit(action,module,rid=None,desc=''):
 if session.get('user_id'): execute('INSERT INTO audit_logs(user_id,username,user_role,action,module,record_id,description) VALUES(%s,%s,%s,%s,%s,%s,%s)',(session['user_id'],session['username'],session['role'],action,module,str(rid or ''),desc))
def login_required(f):
 @wraps(f)
 def w(*a,**k):
  if not session.get('user_id'): return redirect(url_for('login'))
  return f(*a,**k)
 return w
def roles(*allowed):
 def deco(f):
  @wraps(f)
  def w(*a,**k):
   if not session.get('user_id'): return redirect(url_for('login'))
   if session['role'] not in allowed: abort(403)
   return f(*a,**k)
  return w
 return deco
@app.template_filter('money')
def money(v): return '₹{:,.2f}'.format(float(v or 0))
@app.route('/')
def home(): return redirect(url_for('dashboard') if session.get('user_id') else url_for('login'))
@app.route('/login',methods=['GET','POST'])
def login():
 if request.method=='POST':
  u=fetch('SELECT u.*,r.name role FROM users u JOIN roles r ON r.id=u.role_id WHERE username=%s AND is_active=1',(request.form['username'].strip(),),True)
  if u and check_password_hash(u['password_hash'],request.form['password']):
   session.clear(); session.update(user_id=u['id'],username=u['username'],full_name=u['full_name'],role=u['role']); audit('Login','Auth',u['id']); return redirect(url_for('dashboard'))
  flash('Invalid username or password.','danger')
 return render_template('login.html')
@app.route('/logout')
@login_required
def logout(): audit('Logout','Auth'); session.clear(); return redirect(url_for('login'))
@app.route('/dashboard')
@login_required
def dashboard():
 s={'patients':fetch('SELECT COUNT(*) n FROM patients',one=True)['n'],'doctors':fetch('SELECT COUNT(*) n FROM doctors WHERE is_active=1',one=True)['n'],'appointments':fetch('SELECT COUNT(*) n FROM appointments WHERE DATE(appointment_at)=CURDATE()',one=True)['n'],'pending':fetch("SELECT COUNT(*) n FROM appointments WHERE status IN ('Scheduled','Confirmed')",one=True)['n'],'revenue':fetch('SELECT COALESCE(SUM(amount),0) n FROM payments WHERE DATE(paid_at)=CURDATE()',one=True)['n'],'due':fetch("SELECT COALESCE(SUM(total_amount-amount_paid),0) n FROM invoices WHERE status<>'Paid'",one=True)['n'],'admitted':fetch("SELECT COUNT(*) n FROM admissions WHERE status='Admitted'",one=True)['n'],'beds':fetch('SELECT COUNT(*) n FROM beds WHERE is_available=1',one=True)['n']}
 recent=fetch('SELECT * FROM patients ORDER BY id DESC LIMIT 6')
 logs=fetch('SELECT * FROM audit_logs ORDER BY id DESC LIMIT 8') if session['role']=='Admin' else []
 return render_template('dashboard.html',s=s,recent=recent,logs=logs)
@app.route('/patients',methods=['GET','POST'])
@login_required
def patients():
 if request.method=='POST':
  if session['role'] not in ('Admin','Receptionist'): abort(403)
  code='PAT-'+datetime.now().strftime('%y%m%d%H%M%S')
  pid=execute('INSERT INTO patients(patient_code,full_name,dob,gender,blood_group,phone,email,address,emergency_contact,medical_history,created_by) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',(code,request.form['full_name'].strip(),request.form.get('dob') or None,request.form.get('gender'),request.form.get('blood_group'),request.form.get('phone'),request.form.get('email'),request.form.get('address'),request.form.get('emergency_contact'),request.form.get('medical_history'),session['user_id']))
  audit('Patient registered','Patients',pid,code); flash('Patient registered: '+code,'success'); return redirect(url_for('patients'))
 q=request.args.get('q',''); rows=fetch('SELECT * FROM patients WHERE full_name LIKE %s OR patient_code LIKE %s OR phone LIKE %s ORDER BY id DESC',(f'%{q}%',f'%{q}%',f'%{q}%'))
 return render_template('patients.html',rows=rows,q=q)
@app.route('/doctors',methods=['GET','POST'])
@login_required
def doctors():
 if request.method=='POST':
  if session['role']!='Admin': abort(403)
  code='DOC-'+datetime.now().strftime('%y%m%d%H%M%S')
  did=execute('INSERT INTO doctors(doctor_code,full_name,department_id,specialization,qualification,phone,consultation_fee,schedule_text) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)',(code,request.form['full_name'],request.form.get('department_id') or None,request.form.get('specialization'),request.form.get('qualification'),request.form.get('phone'),request.form.get('consultation_fee') or 0,request.form.get('schedule_text')))
  audit('Doctor added','Doctors',did,code); flash('Doctor added.','success'); return redirect(url_for('doctors'))
 return render_template('doctors.html',rows=fetch('SELECT d.*,dp.name department FROM doctors d LEFT JOIN departments dp ON dp.id=d.department_id'),depts=fetch('SELECT * FROM departments'))
@app.route('/appointments',methods=['GET','POST'])
@login_required
def appointments():
 if request.method=='POST':
  if session['role'] not in ('Admin','Receptionist'): abort(403)
  pid=request.form['patient_id']; did=request.form['doctor_id']; at=request.form['appointment_at'].replace('T',' ')
  if fetch("SELECT id FROM appointments WHERE doctor_id=%s AND appointment_at=%s AND status NOT IN ('Cancelled','No-show')",(did,at),True): flash('Doctor already has a booking at this time.','danger')
  else:
   code='APT-'+datetime.now().strftime('%y%m%d%H%M%S'); aid=execute('INSERT INTO appointments(appointment_code,patient_id,doctor_id,appointment_at,reason,created_by) VALUES(%s,%s,%s,%s,%s,%s)',(code,pid,did,at,request.form.get('reason'),session['user_id'])); audit('Appointment booked','Appointments',aid,code); flash('Appointment booked.','success')
  return redirect(url_for('appointments'))
 rows=fetch('SELECT a.*,p.full_name patient,d.full_name doctor FROM appointments a JOIN patients p ON p.id=a.patient_id JOIN doctors d ON d.id=a.doctor_id ORDER BY appointment_at DESC')
 return render_template('appointments.html',rows=rows,patients=fetch('SELECT * FROM patients'),doctors=fetch('SELECT * FROM doctors WHERE is_active=1'))
@app.route('/appointments/<int:i>/status',methods=['POST'])
@login_required
def appt_status(i):
 st=request.form['status']
 if st not in ('Scheduled','Confirmed','Completed','Cancelled','No-show'): abort(400)
 execute('UPDATE appointments SET status=%s WHERE id=%s',(st,i)); audit('Appointment status changed','Appointments',i,st); return redirect(url_for('appointments'))
@app.route('/admissions',methods=['GET','POST'])
@login_required
def admissions():
 if request.method=='POST':
  if session['role'] not in ('Admin','Receptionist'): abort(403)
  c=get_connection(); cur=c.cursor(dictionary=True)
  try:
   cur.execute('SELECT is_available FROM beds WHERE id=%s FOR UPDATE',(request.form['bed_id'],)); b=cur.fetchone()
   if not b or not b['is_available']: flash('Bed is no longer available.','danger')
   else:
    code='ADM-'+datetime.now().strftime('%y%m%d%H%M%S'); cur.execute('INSERT INTO admissions(admission_code,patient_id,bed_id,admitted_at,diagnosis) VALUES(%s,%s,%s,NOW(),%s)',(code,request.form['patient_id'],request.form['bed_id'],request.form.get('diagnosis'))); aid=cur.lastrowid
    cur.execute('UPDATE beds SET is_available=0 WHERE id=%s',(request.form['bed_id'],)); c.commit(); audit('Patient admitted','Admissions',aid,code); flash('Patient admitted.','success')
  except: c.rollback(); raise
  finally: cur.close(); c.close()
  return redirect(url_for('admissions'))
 rows=fetch('SELECT a.*,p.full_name patient,b.bed_code,w.name ward FROM admissions a JOIN patients p ON p.id=a.patient_id JOIN beds b ON b.id=a.bed_id JOIN wards w ON w.id=b.ward_id ORDER BY a.id DESC')
 return render_template('admissions.html',rows=rows,patients=fetch('SELECT * FROM patients'),beds=fetch('SELECT b.*,w.name ward FROM beds b JOIN wards w ON w.id=b.ward_id WHERE is_available=1'))
@app.route('/admissions/<int:i>/discharge',methods=['POST'])
@roles('Admin','Receptionist')
def discharge(i):
 c=get_connection(); cur=c.cursor(dictionary=True)
 try:
  cur.execute("SELECT * FROM admissions WHERE id=%s AND status='Admitted' FOR UPDATE",(i,)); a=cur.fetchone()
  if a:
   cur.execute("UPDATE admissions SET status='Discharged',discharged_at=NOW() WHERE id=%s",(i,)); cur.execute('UPDATE beds SET is_available=1 WHERE id=%s',(a['bed_id'],)); c.commit(); audit('Patient discharged','Admissions',i,a['admission_code'])
 finally: cur.close(); c.close()
 return redirect(url_for('admissions'))
@app.route('/billing',methods=['GET','POST'])
@login_required
def billing():
 if request.method=='POST':
  if session['role'] not in ('Admin','Receptionist'): abort(403)
  fields=['consultation_fee','room_charges','medicine_charges','lab_charges','other_charges','discount']
  v=[Decimal(request.form.get(k) or '0') for k in fields]
  if any(x<0 for x in v) or sum(v[:5])<v[5]: flash('Invalid invoice amounts.','danger'); return redirect(url_for('billing'))
  total=sum(v[:5])-v[5]; code='INV-'+datetime.now().strftime('%y%m%d%H%M%S')
  iid=execute('INSERT INTO invoices(invoice_code,patient_id,consultation_fee,room_charges,medicine_charges,lab_charges,other_charges,discount,total_amount,created_by) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',(code,request.form['patient_id'],*v,total,session['user_id']))
  audit('Invoice generated','Billing',iid,code); flash('Invoice generated.','success'); return redirect(url_for('billing'))
 return render_template('billing.html',rows=fetch('SELECT i.*,p.full_name patient FROM invoices i JOIN patients p ON p.id=i.patient_id ORDER BY i.id DESC'),patients=fetch('SELECT * FROM patients'))
@app.route('/billing/<int:i>/payment',methods=['POST'])
@roles('Admin','Receptionist')
def payment(i):
 amount=Decimal(request.form['amount'])
 c=get_connection(); cur=c.cursor(dictionary=True)
 try:
  cur.execute('SELECT * FROM invoices WHERE id=%s FOR UPDATE',(i,)); inv=cur.fetchone()
  if not inv: abort(404)
  due=Decimal(inv['total_amount'])-Decimal(inv['amount_paid'])
  if amount<=0 or amount>due: flash('Payment must be positive and cannot exceed due balance.','danger')
  else:
   cur.execute('INSERT INTO payments(payment_code,invoice_id,amount,method,reference_no,received_by) VALUES(%s,%s,%s,%s,%s,%s)',('PAY-'+datetime.now().strftime('%y%m%d%H%M%S'),i,amount,request.form['method'],request.form.get('reference_no'),session['user_id']))
   paid=Decimal(inv['amount_paid'])+amount; cur.execute('UPDATE invoices SET amount_paid=%s,status=%s WHERE id=%s',(paid,'Paid' if paid==Decimal(inv['total_amount']) else 'Partially Paid',i)); c.commit(); audit('Payment received','Billing',i,str(amount)); flash('Payment saved.','success')
  c.commit()
 except: c.rollback(); raise
 finally: cur.close(); c.close()
 return redirect(url_for('billing'))
@app.route('/prescriptions',methods=['GET','POST'])
@login_required
def prescriptions():
 if request.method=='POST':
  if session['role'] not in ('Admin','Doctor'): abort(403)
  rid=execute('INSERT INTO prescriptions(patient_id,doctor_id,diagnosis,notes) VALUES(%s,%s,%s,%s)',(request.form['patient_id'],request.form['doctor_id'],request.form.get('diagnosis'),request.form.get('notes')))
  execute('INSERT INTO prescription_items(prescription_id,medicine_name,dosage,frequency,duration,instructions) VALUES(%s,%s,%s,%s,%s,%s)',(rid,request.form['medicine_name'],request.form.get('dosage'),request.form.get('frequency'),request.form.get('duration'),request.form.get('instructions')))
  audit('Prescription created','Prescriptions',rid); flash('Prescription saved.','success'); return redirect(url_for('prescriptions'))
 return render_template('prescriptions.html',rows=fetch('SELECT r.*,p.full_name patient,d.full_name doctor FROM prescriptions r JOIN patients p ON p.id=r.patient_id JOIN doctors d ON d.id=r.doctor_id ORDER BY r.id DESC'),patients=fetch('SELECT * FROM patients'),doctors=fetch('SELECT * FROM doctors'))
@app.route('/inventory',methods=['GET','POST'])
@login_required
def inventory():
 if request.method=='POST':
  if session['role'] not in ('Admin','Receptionist'): abort(403)
  mid=execute('INSERT INTO medicines(name,manufacturer,stock_qty,unit_price,expiry_date,reorder_level) VALUES(%s,%s,%s,%s,%s,%s)',(request.form['name'],request.form.get('manufacturer'),request.form.get('stock_qty') or 0,request.form.get('unit_price') or 0,request.form.get('expiry_date') or None,request.form.get('reorder_level') or 10))
  execute("INSERT INTO inventory_transactions(medicine_id,change_qty,transaction_type,note,created_by) VALUES(%s,%s,'IN','Opening stock',%s)",(mid,request.form.get('stock_qty') or 0,session['user_id'])); audit('Medicine added','Inventory',mid); return redirect(url_for('inventory'))
 return render_template('inventory.html',rows=fetch('SELECT * FROM medicines ORDER BY name'))
@app.route('/inventory/<int:i>/stock',methods=['POST'])
@roles('Admin','Receptionist')
def stock(i):
 qty=int(request.form['qty']); typ=request.form['typ']
 c=get_connection(); cur=c.cursor()
 try:
  cur.execute('SELECT stock_qty FROM medicines WHERE id=%s FOR UPDATE',(i,)); old=cur.fetchone()[0]; new=old+qty if typ=='IN' else old-qty
  if qty<=0 or new<0: flash('Invalid stock adjustment.','danger')
  else:
   cur.execute('UPDATE medicines SET stock_qty=%s WHERE id=%s',(new,i)); cur.execute('INSERT INTO inventory_transactions(medicine_id,change_qty,transaction_type,note,created_by) VALUES(%s,%s,%s,%s,%s)',(i,qty,typ,request.form.get('note'),session['user_id'])); c.commit(); audit('Stock updated','Inventory',i,f'{typ} {qty}')
  c.commit()
 except: c.rollback(); raise
 finally: cur.close(); c.close()
 return redirect(url_for('inventory'))
@app.route('/reports')
@roles('Admin')
def reports():
 return render_template('reports.html',rev=fetch("SELECT DATE_FORMAT(paid_at,'%Y-%m') month,SUM(amount) total FROM payments GROUP BY month ORDER BY month DESC"),states=fetch('SELECT status,COUNT(*) total FROM appointments GROUP BY status'))
@app.route('/audit-logs')
@roles('Admin')
def audit_logs(): return render_template('audit.html',rows=fetch('SELECT * FROM audit_logs ORDER BY id DESC LIMIT 300'))
@app.errorhandler(403)
def forbidden(e): return render_template('error.html',code=403,msg='Access denied for your account role.'),403
@app.errorhandler(404)
def missing(e): return render_template('error.html',code=404,msg='Requested page or record was not found.'),404
if __name__=='__main__': init_pool(); app.run(debug=True)
