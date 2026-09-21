from django.test import SimpleTestCase, RequestFactory, override_settings
from django.template.loader import render_to_string
from .context import site_brand


class BrandMetadataTests(SimpleTestCase):
    @override_settings(PUBLIC_URL='https://race.example')
    def test_share_urls_use_public_domain_without_search_parameters(self):
        request = RequestFactory().get('/results/?q=Private+search')
        context = site_brand(request)
        html = render_to_string('brand_metadata.html', context)
        self.assertIn('content="https://race.example/results/"', html)
        self.assertIn('content="https://race.example/static/images/brand/share.png"', html)
        self.assertNotIn('Private', html)

    def test_conventional_favicon_resolves_to_official_asset(self):
        response = self.client.get('/favicon.ico')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/static/images/brand/icon-32.png')
