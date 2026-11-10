"""Fictional consolidated workbook with saved formula results, never client data."""
from io import BytesIO
from openpyxl import load_workbook
from fixtures import make_semantic_workbook, with_cached_values


def make_consolidated_workbook():
    workbook=load_workbook(BytesIO(make_semantic_workbook(advisor_owner=False)))
    main=workbook['Remediations'];main.title='CMA, WIFI, VA Remediations'
    main['S3']='Type Of Remediation'
    ot=workbook['OT'];ot.title='OT Remediations';ot['H1']='Year'
    all_=workbook.create_sheet('All Remediations')
    all_.append(['Remediation','Domain','Remediation name','Budget Global','Budget Local - Complete',
                 'Budget Local - Business Oriented','BUDGET LOCAL TOT','Year','NIS2','Owner','Priority',
                 'Type Of Remediation','Risk Type\n(Cyber, OT, Business Continuity, Compliance)',
                 'Impact type\n(Reputational, Regulatory, Economic, Operational)','Risk Level','CAPEX/OPEX','Note'])
    rows=[
      ['R.1','Governance','Demo governance',1000,100,10,'=E2*13+F2*8',2027,'Yes','ADVISOR','Yes','Process','Cyber\nCompliance','Economic\nRegulatory','High','CAPEX','If implemented on an automated platform.'],
      ['R.2','Security','Demo backup',2000,200,0,'=$E$3*5+$F$3*8',2028,'No','Supplier B','No','Technology','Cyber','Operational','Medium','OPEX','-'],
      ['R.2','Security','Demo alignment',3000,50,20,'=E4*13+F4*8',2028,'Yes','Supplier A',None,'Process','Cyber\nCompliance','Economic\nOperational','Low','OPEX','-'],
      ['R.OT.1','Security','Demo OT 1',500,20,None,'=E5*6',2027,'Yes',None,None,'Process','OT\nCompliance','Operational\nRegulatory','High','OPEX','-'],
      ['R.OT.2','Security','Demo OT 2',700,30,None,'=E6*6',2028,'Yes',None,None,'People','OT','Operational','High','OPEX','-'],
      ['R.N','Compliance','Annual alignment',70,12,12,'=E7*7+F7*1',2027,'Yes','ADVISOR',None,'Process','Cyber\nCompliance','Regulatory','High','OPEX','-'],
      ['R.N','Compliance','Annual alignment',70,12,12,'=E8*7+F8*1',2028,'Yes','ADVISOR',None,'Process','Cyber\nCompliance','Regulatory','High','OPEX','-'],
    ]
    for row in rows:all_.append(row)
    # Extra sheets must never add budget a second time.
    duplicate=workbook.create_sheet('Budget TOTAL');duplicate.append(['Global',99999999])
    output=BytesIO();workbook.save(output);workbook.close()
    return with_cached_values(output.getvalue(),{
        'xl/worksheets/sheet2.xml':{'L4':1380,'L5':1000,'L6':810,'L7':0,'L8':0,'I9':6400,'L9':3190},
        'xl/worksheets/sheet3.xml':{'G2':120,'G3':180},
        'xl/worksheets/sheet4.xml':{'G2':1380,'G3':1000,'G4':810,'G5':120,'G6':180,'G7':96,'G8':96},
    })
