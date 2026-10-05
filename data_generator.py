import pandas as pd
import numpy as np
from faker import Faker
import random
import json
from datetime import datetime, timedelta

# Configuración inicial
fake = Faker()
Faker.seed(42)
random.seed(42)

NUM_CUSTOMERS = 2500
START_DATE = datetime(2022, 1, 1)
END_DATE = datetime(2024, 1, 1)

def generate_dirty_crm():
    customers = []
    
    for _ in range(NUM_CUSTOMERS):
        customer_id = fake.uuid4()
        signup_date = fake.date_between(start_date=START_DATE, end_date=END_DATE - timedelta(days=30))
        
        # 1. Ruido en los planes y MRR
        plan_base = random.choice(['Basic', 'Pro', 'Enterprise'])
        dirty_plan = plan_base
        if random.random() < 0.05: # 5% de errores tipográficos
            dirty_plan = random.choice(['basico', 'PR0', ' enterprise ', 'Basic Plan'])
            
        mrr_dict = {'Basic': 29, 'Pro': 99, 'Enterprise': 299}
        mrr = mrr_dict.get(plan_base, 99)
        
        # Ensuciar MRR (símbolos, negativos, strings)
        if random.random() < 0.05: mrr = f"${mrr}"
        elif random.random() < 0.02: mrr = -mrr 
        elif random.random() < 0.03: mrr = np.nan
            
        # 2. Lógica de Churn (~25% de tasa de cancelación)
        is_churned = random.random() < 0.25
        status = 'Churned' if is_churned else 'Active'
        
        churn_date = None
        if is_churned:
            days_active = random.randint(30, (END_DATE.date() - signup_date).days)
            churn_date = signup_date + timedelta(days=days_active)
            
        # 3. Ruido en Fechas (mezclar formatos)
        signup_str = signup_date.strftime("%Y-%m-%d")
        if random.random() < 0.1:
            signup_str = signup_date.strftime("%d/%m/%Y") # Formato europeo mezclado
            
        churn_str = churn_date.strftime("%Y-%m-%d") if churn_date else None
            
        # 4. Ruido en Industria
        industry = random.choice(['SaaS', 'E-commerce', 'Finance', 'Healthcare', 'Marketing'])
        if random.random() < 0.08: industry = np.nan # 8% valores nulos
            
        customers.append({
            'customer_id': customer_id,
            'company_name': fake.company(),
            'industry': industry,
            'plan_type': dirty_plan,
            'mrr': mrr,
            'signup_date': signup_str,
            'status': status,
            'churn_date': churn_str
        })
        
    df_crm = pd.DataFrame(customers)
    df_crm.to_csv('crm_suscripciones.csv', index=False)
    print(f"✅ CRM generado con {len(df_crm)} registros.")
    return df_crm

def generate_activity_logs(df_crm):
    logs = []
    
    for _, row in df_crm.iterrows():
        # Tratar la fecha de signup dependiendo del formato sucio que hayamos creado
        try:
            start_date = datetime.strptime(str(row['signup_date']), "%Y-%m-%d").date()
        except:
            start_date = datetime.strptime(str(row['signup_date']), "%d/%m/%Y").date()
            
        end_period = END_DATE.date()
        if row['status'] == 'Churned' and pd.notna(row['churn_date']):
            end_period = datetime.strptime(str(row['churn_date']), "%Y-%m-%d").date()
            
        current_date = start_date
        
        # Generar un log semanal por cliente
        while current_date <= end_period:
            days_to_churn = (end_period - current_date).days if row['status'] == 'Churned' else 999
            
            # LÓGICA DE NEGOCIO: Si falta poco para el churn, bajan las métricas
            if days_to_churn < 45: 
                logins = random.randint(0, 2)
                tasks = random.randint(0, 5)
                session_mins = random.randint(0, 30)
            else:
                # Comportamiento normal según plan
                if 'Basic' in str(row['plan_type']):
                    logins, tasks, session_mins = random.randint(2, 5), random.randint(10, 50), random.randint(60, 200)
                else:
                    logins, tasks, session_mins = random.randint(4, 15), random.randint(40, 200), random.randint(150, 500)
            
            # Ruido en los logs (outliers imposibles y faltas de datos)
            if random.random() < 0.005: session_mins = 99999 # Outlier
            if random.random() < 0.01: logins = None # Valor nulo
                
            logs.append({
                'log_id': fake.uuid4(),
                'customer_id': row['customer_id'],
                'week_start': current_date.strftime("%Y-%m-%d"),
                'logins_count': logins,
                'tasks_created': tasks,
                'session_duration_mins': session_mins
            })
            
            current_date += timedelta(days=7)
            
    with open('logs_actividad.json', 'w') as f:
        json.dump(logs, f)
    print(f"✅ Logs generados con {len(logs)} registros.")

# Ejecutar el proceso
print("Generando datos simulados para TaskFlow...")
crm_data = generate_dirty_crm()
generate_activity_logs(crm_data)
print("¡Proceso completado! Revisa los archivos generados en tu carpeta.")