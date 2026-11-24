import unittest
from complaint_ai import analyze_complaint, find_similar_complaints


class ComplaintAITests(unittest.TestCase):
    def test_wifi_complaint_suggests_it_support(self):
        result = analyze_complaint('WiFi not working', 'Internet connection in computer lab is broken')
        self.assertEqual(result['category'], 'IT Support')
        self.assertIn(result['priority'], {'Low', 'Medium', 'High'})
        self.assertEqual(result['model_type'], 'transparent-rule-based-v1')

    def test_safety_language_is_high_priority_advisory(self):
        result = analyze_complaint('Electrical issue', 'There are exposed wires and sparks near a classroom')
        self.assertEqual(result['priority'], 'High')

    def test_similar_complaint_is_returned(self):
        rows = [{'complaint_id': 12, 'title': 'WiFi connection issue', 'description': 'Internet not working in lab', 'status': 'Pending'}]
        found = find_similar_complaints('WiFi issue', 'Internet is not working in the lab', rows)
        self.assertTrue(found)
        self.assertEqual(found[0]['complaint_id'], 12)


if __name__ == '__main__':
    unittest.main()
