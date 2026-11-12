"""Create synthetic decks only, for Microsoft's Open XML validator in CI."""
from io import BytesIO
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from pptx import Presentation
from app.presentation import create_presentation,_notes
from test_presentation import report_fixture,stress_report

output=Path(sys.argv[1]);output.mkdir(parents=True,exist_ok=True)
for scope in ('all','global','local'):
    report=report_fixture();report['scope']=scope
    content=create_presentation(report)
    Presentation(BytesIO(content))
    (output/f'{scope}.pptx').write_bytes(content)
(output/'large-project.pptx').write_bytes(create_presentation(stress_report()))
prs=Presentation();slide=prs.slides.add_slide(prs.slide_layouts[6])
_notes(slide,'SYNTHETIC LONG NOTES '*550000)
prs.save(output/'large-notes.pptx')
