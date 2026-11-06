from werkzeug.security import generate_password_hash
from database.db import get_connection
c=get_connection(); x=c.cursor()
try:
 for r in ('Admin','Doctor','Receptionist'): x.execute('INSERT IGNORE INTO roles(name) VALUES(%s)',(r,))
 x.execute("SELECT id FROM roles WHERE name='Admin'"); rid=x.fetchone()[0]
 x.execute('INSERT IGNORE INTO users(username,password_hash,full_name,role_id) VALUES(%s,%s,%s,%s)',('admin',generate_password_hash('Admin@123'),'System Administrator',rid))
 for d in ('General Medicine','Cardiology','Orthopaedics','Paediatrics','Dermatology'): x.execute('INSERT IGNORE INTO departments(name) VALUES(%s)',(d,))
 x.execute('SELECT id FROM departments ORDER BY id'); depts=[r[0] for r in x.fetchall()]
 docs=[('Dr. A. Sharma','General Medicine',500),('Dr. R. Sen','Cardiology',800),('Dr. P. Das','Orthopaedics',700),('Dr. N. Roy','Paediatrics',600),('Dr. S. Khan','Dermatology',650)]
 for i,(n,s,f) in enumerate(docs,1): x.execute('INSERT IGNORE INTO doctors(doctor_code,full_name,department_id,specialization,qualification,consultation_fee,schedule_text) VALUES(%s,%s,%s,%s,%s,%s,%s)',(f'DOC-{i:03}',n,depts[i-1],s,'MBBS, MD',f,'Mon-Sat 10 AM-5 PM'))
 for i in range(1,16): x.execute('INSERT IGNORE INTO patients(patient_code,full_name,dob,gender,blood_group,phone,email,address,medical_history) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)',(f'PAT-{i:04}',f'Sample Patient {i}',f'{1980+i}-01-15','Male' if i%2 else 'Female',['A+','B+','O+','AB+'][i%4],f'90000000{i:02}',f'p{i}@demo.local','Kolkata, West Bengal','No known history'))
 for i in range(1,6): x.execute('INSERT IGNORE INTO wards(name,ward_type) VALUES(%s,%s)',(f'General Ward {i}','General'))
 x.execute('SELECT id FROM wards ORDER BY id'); wards=[r[0] for r in x.fetchall()]
 for i in range(1,16): x.execute('INSERT IGNORE INTO beds(bed_code,ward_id) VALUES(%s,%s)',(f'BED-{i:03}',wards[(i-1)%5]))
 for i in range(1,11): x.execute("INSERT IGNORE INTO appointments(appointment_code,patient_id,doctor_id,appointment_at,reason) VALUES(%s,%s,%s,DATE_ADD(NOW(),INTERVAL %s DAY),'Routine consultation')",(f'APT-{i:04}',i,(i-1)%5+1,i%7))
 for i in range(1,11): x.execute('INSERT INTO medicines(name,manufacturer,stock_qty,unit_price,expiry_date,reorder_level) SELECT %s,%s,50,15.00,%s,10 WHERE NOT EXISTS(SELECT 1 FROM medicines WHERE name=%s)',(f'Medicine {i}','Demo Pharma','2027-12-31',f'Medicine {i}'))
 c.commit()
finally: x.close(); c.close()
print('Seed complete. Login: admin / Admin@123')
