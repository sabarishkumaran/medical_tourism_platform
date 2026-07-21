from django.test import TestCase
from django.urls import reverse
from accounts.models import User, Country
from hospitals.models import Accreditation

class AdminConfigAndProfileTests(TestCase):
    def setUp(self):
        self.patient = User.objects.create_user(
            username='patient_user', email='patient@test.com', password='password123', role='PATIENT'
        )
        self.coordinator = User.objects.create_user(
            username='coordinator_user', email='coord@test.com', password='password123', role='COORDINATOR'
        )
        self.admin = User.objects.create_superuser(
            username='admin_user', email='admin@test.com', password='password123'
        )

    def test_profile_does_not_contain_django_admin_link(self):
        self.client.login(username='admin_user', password='password123')
        response = self.client.get(reverse('profile'))
        self.assertNotContains(response, '<a href="/admin"')

    def test_admin_config_permissions(self):
        # 1. Patient should be denied / redirected
        self.client.login(username='patient_user', password='password123')
        response = self.client.get(reverse('admin_global_config'))
        self.assertRedirects(response, reverse('home'))

        # 2. Coordinator should be allowed access
        self.client.login(username='coordinator_user', password='password123')
        response = self.client.get(reverse('admin_global_config'))
        self.assertEqual(response.status_code, 200)

        # 3. Admin should be allowed access
        self.client.login(username='admin_user', password='password123')
        response = self.client.get(reverse('admin_global_config'))
        self.assertEqual(response.status_code, 200)

    def test_add_and_delete_country_and_accreditation(self):
        self.client.login(username='coordinator_user', password='password123')
        
        # Add Country
        response = self.client.post(reverse('admin_global_config'), {
            'action': 'add_country',
            'name': 'Testland',
            'code': 'TL'
        })
        self.assertTrue(Country.objects.filter(name='Testland').exists())

        # Add Accreditation
        response = self.client.post(reverse('admin_global_config'), {
            'action': 'add_accreditation',
            'name': 'Test Accreditation Board',
            'code': 'TAB'
        })
        self.assertTrue(Accreditation.objects.filter(code='TAB').exists())

        # Delete Country
        country_obj = Country.objects.get(name='Testland')
        response = self.client.post(reverse('admin_global_config'), {
            'action': 'delete_country',
            'country_id': country_obj.id
        })
        self.assertFalse(Country.objects.filter(name='Testland').exists())

        # Delete Accreditation
        acc_obj = Accreditation.objects.get(code='TAB')
        response = self.client.post(reverse('admin_global_config'), {
            'action': 'delete_accreditation',
            'accreditation_id': acc_obj.id
        })
        self.assertFalse(Accreditation.objects.filter(code='TAB').exists())
