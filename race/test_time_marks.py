from django.test import SimpleTestCase
from django.core.exceptions import ValidationError
from .time_marks import time_seconds


class TimeMarksTests(SimpleTestCase):
    def test_formats_normalize_to_seconds(self):
        for value, mode, expected in [('15','seconds',15), ('15.25','seconds',15.25),
                ('5.365','minutes',321.9), ('5,365','minutes',321.9),
                ('5:36.5','minutes_seconds',336.5), ('0:15.25','minutes_seconds',15.25)]:
            with self.subTest(value=value):
                self.assertEqual(time_seconds(value,mode),expected)

    def test_invalid_and_ambiguous_inputs_are_rejected(self):
        for value, mode in [('5:60','minutes_seconds'), ('5.365','minutes_seconds'),
                ('5:36','seconds'), ('NaN','seconds'), ('-1','minutes'), ('0','seconds'),
                ('1','unknown'), ('5:36:5','minutes_seconds')]:
            with self.subTest(value=value,mode=mode):
                with self.assertRaises(ValidationError):time_seconds(value,mode)

    def test_dot_minutes_and_decimal_seconds_have_distinct_meanings(self):
        self.assertEqual(time_seconds('25.15','minutes_seconds_dot'),1515)
        self.assertEqual(time_seconds('25.15','seconds'),25.15)
        self.assertEqual(time_seconds('25.015','seconds'),25.015)
        for value in ['25.60','25.99','25.1']:
            with self.assertRaises(ValidationError):time_seconds(value,'minutes_seconds_dot')
