import pandas as pd
import numpy as np
from faker import Faker
import random
import json
from datetime import datetime, timedelta

# Configuración inicial
fake = Faker()
Faker.seed(101)
random.seed(101)
np.random.seed(101)

# ESCALADO: 15,000 clientes generarán ~800k - 1 Millón de logs
NUM_CUSTOMERS = 15000 
START_DATE = datetime(2022, 1, 1)
END_DATE = datetime(2024, 1, 1)

def generate_realistic_crm():
    customers = []
    
    for _ in range(NUM_CUSTOMERS):
        customer_id = fake.uuid4()
        
        # Realismo: Más altas recientes simulando el crecimiento de una startup
        days_total = (END_DATE - START_DATE).days
        random_days = int(np.random.beta(a=2, b=1) * days_total) 
        signup_date = START_DATE + timedelta(days=random_days)
        
        # Distribución lógica de planes (Pirámide de precios)
        plan_base = np.random.choice(
            ['Basic', 'Pro', 'Enterprise'], 
            p=[0.65, 0.28, 0.07]
        )
        
        dirty_plan = plan_base
        # Errores drásticamente reducidos (solo 1.5% de la base tendrá errores de nombre)
        if random.random() < 0.015: 
            dirty_plan = random.choice(['basico', 'PR0', ' enterprise ', 'Basic Plan', 'Test'])
            
        mrr_dict = {'Basic': 29, 'Pro': 99, 'Enterprise': 299}
        mrr = mrr_dict.get(plan_base, 0)
        
        # Errores financieros esporádicos
        if random.random() < 0.01: mrr = f"${mrr}"     # 1% con símbolo $
        elif random.random() < 0.005: mrr = -mrr       # 0.5% errores de facturación (negativo)
        elif random.random() < 0.005: mrr = np.nan     # 0.5% nulos
            
        # Lógica de Churn realista: Los planes básicos cancelan más que los Enterprise
        churn_prob = {'Basic': 0.35, 'Pro': 0.15, 'Enterprise': 0.05}.get(plan_base, 0.2)
        is_churned = random.random() < churn_prob
        status = 'Churned' if is_churned else 'Active'
        
        churn_date = None
        if is_churned:
            # Realismo: La mayoría cancela en los primeros 3-6 meses
            max_active_days = (END_DATE.date() - signup_date.date()).days
            if max_active_days > 30:
                days_active = int(np.random.exponential(scale=120))
                days_active = min(max(days_active, 15), max_active_days)
                churn_date = signup_date + timedelta(days=days_active)
            else:
                status = 'Active' # Si no hay tiempo material para cancelar, sigue activo
            
        # Ruido esporádico en Fechas
        signup_str = signup_date.strftime("%Y-%m-%d")
        if random.random() < 0.02: # Solo un 2% de fechas en formato europeo
            signup_str = signup_date.strftime("%d/%m/%Y") 
            
        churn_str = churn_date.strftime("%Y-%m-%d") if churn_date else None
            
        # Industrias con pequeños errores
        industry = np.random.choice(
            ['SaaS', 'E-commerce', 'Finance', 'Healthcare', 'Marketing', 'Education'],
            p=[0.3, 0.25, 0.15, 0.1, 0.1, 0.1]
        )
        if random.random() < 0.03: industry = np.nan # Solo 3% nulos
            
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
        try:
            start_date = datetime.strptime(str(row['signup_date']), "%Y-%m-%d").date()
        except:
            start_date = datetime.strptime(str(row['signup_date']), "%d/%m/%Y").date()
            
        end_period = END_DATE.date()
        if row['status'] == 'Churned' and pd.notna(row['churn_date']):
            end_period = datetime.strptime(str(row['churn_date']), "%Y-%m-%d").date()
            
        current_date = start_date
        
        while current_date <= end_period:
            days_to_churn = (end_period - current_date).days if row['status'] == 'Churned' else 999
            
            # Base usage depending on plan
            if 'Basic' in str(row['plan_type']):
                base_logins, base_tasks, base_mins = 3, 15, 90
            elif 'Pro' in str(row['plan_type']):
                base_logins, base_tasks, base_mins = 6, 45, 200
            else:
                base_logins, base_tasks, base_mins = 12, 120, 450
                
            # REALISMO: Desgaste progresivo antes del Churn (no de golpe)
            if days_to_churn < 14:
                multiplier = 0.1 # Prácticamente inactivo las últimas 2 semanas
            elif days_to_churn < 45:
                multiplier = 0.4 # Baja la actividad a menos de la mitad
            elif days_to_churn < 90:
                multiplier = 0.7 # Empieza el desinterés
            else:
                # Fluctuación natural semanal (+/- 30%)
                multiplier = random.uniform(0.7, 1.3)
                
            logins = int(base_logins * multiplier)
            tasks = int(base_tasks * multiplier)
            session_mins = int(base_mins * multiplier)
            
            # Outliers muy raros (0.1% o 0.5%)
            if random.random() < 0.001: session_mins = 99999 
            if random.random() < 0.005: logins = None 
                
            logs.append({
                'log_id': fake.uuid4(),
                'customer_id': row['customer_id'],
                'week_start': current_date.strftime("%Y-%m-%d"),
                'logins_count': logins,
                'tasks_created': tasks,
                'session_duration_mins': session_mins
            })
            
            current_date += timedelta(days=7)
            
    # Guardar en JSON (esto puede tardar unos 20-40 segundos por el volumen)
    with open('logs_actividad.json', 'w') as f:
        json.dump(logs, f)
    print(f"✅ Logs generados con {len(logs)} registros (Aprox. {(len(logs)*150/1024/1024):.2f} MB).")

print("Generando volumen masivo de datos para TaskFlow...")
crm_data = generate_realistic_crm()
generate_activity_logs(crm_data)
print("¡Proceso completado con éxito!")