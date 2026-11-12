"""Editable PPT reconciliation stays compact and agrees with source snapshots."""
from io import BytesIO
import json
import unittest

from pptx import Presentation

from app.presentation import create_presentation
from app.presentation_data import build_presentation_data
from app.workbook import parse_workbook
from fixtures import make_semantic_workbook


class PresentationReconciliationTests(unittest.TestCase):
    def report(self, scope='all', **changes):
        document = parse_workbook(make_semantic_workbook(), 'semantic.xlsx')
        document['project'] = {'id': 'project', 'name': 'Semantic project'}
        request = {'projectId': 'project', 'rowKeys': [row['key'] for row in document['rows']],
                   'entities': None, 'scope': scope, 'filters': {}}
        request.update(changes)
        return build_presentation_data(document, request)

    def deck(self, report):
        return Presentation(BytesIO(create_presentation(report)))

    def annual_slide(self, deck):
        return next(slide for slide in deck.slides if any(
            shape.name == 'dvt-title' and shape.text == 'Budget per anno' for shape in slide.shapes))

    def test_existing_annual_slide_shows_categories_base_delta_and_residual(self):
        report = self.report()
        deck = self.deck(report)
        self.assertLessEqual(len(deck.slides), 15)
        annual = self.annual_slide(deck)
        text = '\n'.join(shape.text for shape in annual.shapes if shape.has_text_frame)
        for expected in ('Base e delta OT', 'Global di gruppo', 'Local Complete + OT · 6 LE',
                         'Local Complete senza OT · 7 LE', 'Local Business · 8 LE', '1.900 €',
                         'Local senza attribuzione certa: 810 €'):
            self.assertIn(expected, text)
        notes = annual.notes_slide.notes_text_frame.text
        self.assertIn(json.dumps(report['budgetBreakdown'], ensure_ascii=False, sort_keys=True), notes)
        self.assertIn('Advisor', '\n'.join(shape.text for slide in deck.slides
                                           for shape in slide.shapes if shape.has_text_frame))
        # This checks the new card/chart layout, not only the legacy fixture.
        for slide in deck.slides:
            for shape in slide.shapes:
                self.assertGreaterEqual(shape.left, -2)
                self.assertGreaterEqual(shape.top, -2)
                self.assertLessEqual(shape.left + shape.width, deck.slide_width + 2)
                self.assertLessEqual(shape.top + shape.height, deck.slide_height + 2)

    def test_global_scope_has_no_local_category_cards_and_one_native_series(self):
        annual = self.annual_slide(self.deck(self.report(scope='global')))
        text = '\n'.join(shape.text for shape in annual.shapes if shape.has_text_frame)
        self.assertIn('Global di gruppo', text)
        self.assertNotIn('Local Complete + OT', text)
        chart = next(shape.chart for shape in annual.shapes if shape.has_chart)
        self.assertEqual([series.name for series in chart.series], ['Global'])
        self.assertEqual(sum(chart.series[0].values), 7600)

    def test_local_scope_keeps_delta_and_unknown_entity_estimates_distinct(self):
        report = self.report(scope='local', entities=['Demo Entity 01'], rowKeys=['Remediations:8'])
        annual = self.annual_slide(self.deck(report))
        text = '\n'.join(shape.text for shape in annual.shapes if shape.has_text_frame)
        self.assertIn('Local Complete + OT · 1 LE', text)
        self.assertIn('Non stimato', text)
        self.assertNotIn('stime mancanti', text)
        self.assertNotIn('Global di gruppo', text)
        self.assertEqual(report['budgetBreakdown']['categories'][0]['baseMissing'], 1)
        self.assertEqual(report['budgetBreakdown']['categories'][0]['baseKnown'], 0)
