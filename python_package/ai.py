import os, json, re
from datetime import datetime
import requests
from openai import OpenAI
from . import models, config
from .ntp import ntp_time

KEY_DEEP = os.path.join(config.BASE_DIR, 'deepseek.key')
KEY_DOUBAO = os.path.join(config.BASE_DIR, 'doubao.key')

def get_key(path):
    if not os.path.exists(path): raise FileNotFoundError(f"Missing {os.path.basename(path)}")
    return open(path,'r',encoding='utf-8').read().strip()

def call_deepseek(prompt, task='manual'):
    k = get_key(KEY_DEEP)
    r = requests.post('https://api.deepseek.com/v1/chat/completions', headers={'Content-Type':'application/json','Authorization':f'Bearer {k}'}, json={
        'model':'deepseek-chat','messages':[{'role':'system','content':'课堂管理助手'},{'role':'user','content':prompt}],'temperature':0.7,'max_tokens':2000}, timeout=30)
    r.raise_for_status()
    return r.json()['choices'][0]['message']['content'].strip()

def classify_action(name):
    try:
        client = OpenAI(base_url='https://ark.cn-beijing.volces.com/api/v3', api_key=get_key(KEY_DOUBAO))
        examples = "\n".join(f"{a['name']} -> {a['category']}/{a['subcategory']}" for a in models.load_actions() if a.get('category'))
        resp = client.responses.create(model='ep-20260722153409-qmxgd', input=[{'role':'user','content':[{'type':'input_text','text':f"分类：{name}\n已有：{examples}\nJSON: {{\"category\":\"奖励或惩罚\",\"subcategory\":\"\"}}"}]}])
        txt = resp.output_text if hasattr(resp,'output_text') else str(resp)
        return json.loads(re.sub(r'```json|```','',txt).strip())
    except:
        return rule_based(name)

def rule_based(name):
    if any(k in name for k in ['积极','帮助','优秀','表扬','认真','完成','进步']): return {"category":"奖励","subcategory":"课堂表现"}
    if any(k in name for k in ['讲话','迟到','未完成','违纪','打架','睡觉','玩手机']): return {"category":"惩罚","subcategory":"课堂违纪"}
    return {"category":"奖励","subcategory":"其他"}

def generate_daily_report(class_list=None):
    all_stu = models.load_all_students() if class_list is None else {u:i for c in class_list for u,i in models.load_class_students(c).items()}
    today = ntp_time().date()
    recs = {}
    for uname, info in all_stu.items():
        if info.get('role')!='student': continue
        cls = info.get('class','未知')
        for r in info.get('records',[]):
            try:
                if datetime.strptime(r['time'],'%Y-%m-%d %H:%M:%S').date()==today:
                    recs.setdefault(cls,[]).append(f"{r['display_time']} {info.get('name',uname)} {r['action']}")
            except: pass
    if not recs:
        save_report(f"# {today} 日报\n\n无记录", 'daily_auto')
        return
    prompt = "\n".join([f"## {c}\n"+"\n".join(rs) for c,rs in recs.items()])
    full = f"总结：\n1. 概况\n2. 班级对比\n3. 行为统计\n4. 异常\n5. 建议\n记录：\n{prompt}"
    save_report(call_deepseek(full,'daily_auto'), 'daily_auto')

def save_report(content, typ):
    reps = models.load_reports()
    n = ntp_time()
    reps.append({'date':n.strftime('%Y-%m-%d'),'time':n.strftime('%H:%M:%S'),'content':content,'type':typ,'scope':'pending'})
    models.save_reports(reps)