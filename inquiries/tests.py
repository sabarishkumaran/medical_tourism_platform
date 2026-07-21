from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from accounts.models import User
from treatments.models import Treatment
from hospitals.models import Hospital
from inquiries.models import Inquiry
from reviews.models import Review, PatientReview
from payments.models import Payment

class PaymentTicketReviewTests(TestCase):
    def setUp(self):
        # Create users
        self.patient_user = User.objects.create_user(
            username='patient1', email='patient@test.com', password='password123', role='PATIENT'
        )
        self.hospital_user = User.objects.create_user(
            username='hospital1', email='hospital@test.com', password='password123', role='HOSPITAL'
        )
        self.admin_user = User.objects.create_superuser(
            username='admin1', email='admin@test.com', password='password123'
        )
        
        # Create hospital details
        self.hospital = Hospital.objects.create(
            user=self.hospital_user,
            name="Test Hospital",
            address="123 Hospital St",
            city="Test City",
            description="Test Desc",
            established_year=2000,
            status="APPROVED"
        )
        
        # Create treatment
        self.treatment = Treatment.objects.create(
            name="Test Treatment",
            description="Treatment Desc"
        )
        
        # Create Inquiry
        self.inquiry = Inquiry.objects.create(
            patient=self.patient_user,
            hospital=self.hospital,
            treatment=self.treatment,
            description="Medical help request",
            travel_date=timezone.now().date() + timedelta(days=20),
            status="PAYMENT_LINK_SENT"
        )

    def test_payment_choices(self):
        # 1. Full Payment
        self.client.login(username='patient1', password='password123')
        response = self.client.post(
            reverse('process_payment', args=[self.inquiry.uuid]),
            {'payment_choice': 'full', 'visa': 'on'}
        )
        self.inquiry.refresh_from_db()
        self.assertEqual(self.inquiry.payment_status, 'FULL')
        self.assertTrue(self.inquiry.booking_confirmed)
        self.assertEqual(self.inquiry.status, 'COMPLETED')
        self.assertEqual(Payment.objects.filter(inquiry=self.inquiry).count(), 1)
        
        # Reset and test Partial
        self.inquiry.payment_status = 'UNPAID'
        self.inquiry.booking_confirmed = False
        self.inquiry.status = 'PAYMENT_LINK_SENT'
        self.inquiry.save()
        Payment.objects.all().delete()
        
        # 2. Partial Payment
        response = self.client.post(
            reverse('process_payment', args=[self.inquiry.uuid]),
            {'payment_choice': 'partial'}
        )
        self.inquiry.refresh_from_db()
        self.assertEqual(self.inquiry.payment_status, 'PARTIAL')
        self.assertTrue(self.inquiry.booking_confirmed)
        
        # Reset and test Unpaid
        self.inquiry.payment_status = 'UNPAID'
        self.inquiry.booking_confirmed = False
        self.inquiry.status = 'PAYMENT_LINK_SENT'
        self.inquiry.save()
        Payment.objects.all().delete()
        
        # 3. Proceed Unpaid
        response = self.client.post(
            reverse('process_payment', args=[self.inquiry.uuid]),
            {'payment_choice': 'unpaid'}
        )
        self.inquiry.refresh_from_db()
        self.assertEqual(self.inquiry.payment_status, 'UNPAID')
        self.assertFalse(self.inquiry.booking_confirmed)

    def test_ticket_upload_deadlines(self):
        self.client.login(username='patient1', password='password123')
        
        # Case A: Unpaid booking (requires 2 weeks / 14 days before travel)
        # Travel date is in 20 days (days_remaining = 20 >= 14) -> Should succeed
        import tempfile
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        test_file = SimpleUploadedFile("ticket.pdf", b"file_content", content_type="application/pdf")
        response = self.client.post(
            reverse('upload_ticket', args=[self.inquiry.uuid]),
            {'ticket_file': test_file}
        )
        self.inquiry.refresh_from_db()
        self.assertTrue(self.inquiry.booking_confirmed)
        self.assertIsNotNone(self.inquiry.ticket_file)
        
        # Reset ticket
        self.inquiry.ticket_file = None
        self.inquiry.booking_confirmed = False
        self.inquiry.save()
        
        # Set travel date to 10 days from now (violates 14 days unpaid requirement)
        self.inquiry.travel_date = timezone.now().date() + timedelta(days=10)
        self.inquiry.save()
        
        test_file = SimpleUploadedFile("ticket.pdf", b"file_content", content_type="application/pdf")
        response = self.client.post(
            reverse('upload_ticket', args=[self.inquiry.uuid]),
            {'ticket_file': test_file}
        )
        self.inquiry.refresh_from_db()
        self.assertFalse(self.inquiry.booking_confirmed) # Should fail confirmation

        # Case B: Paid booking (requires 1 week / 7 days before travel)
        self.inquiry.payment_status = 'PARTIAL'
        self.inquiry.booking_confirmed = True
        self.inquiry.save()
        
        # Travel date is 10 days from now (days_remaining = 10 >= 7) -> Should succeed
        test_file = SimpleUploadedFile("ticket.pdf", b"file_content", content_type="application/pdf")
        response = self.client.post(
            reverse('upload_ticket', args=[self.inquiry.uuid]),
            {'ticket_file': test_file}
        )
        self.inquiry.refresh_from_db()
        self.assertTrue(self.inquiry.booking_confirmed)

    def test_mutual_reviews_and_commissions(self):
        # Setup finished inquiry
        self.inquiry.status = "COMPLETED"
        self.inquiry.payment_status = "PARTIAL"
        self.inquiry.booking_confirmed = True
        self.inquiry.travel_date = timezone.now().date() - timedelta(days=5) # In the past
        self.inquiry.save()
        
        # Hospital completes treatment
        self.client.login(username='hospital1', password='password123')
        response = self.client.post(reverse('mark_treatment_completed', args=[self.inquiry.uuid]))
        self.inquiry.refresh_from_db()
        self.assertTrue(self.inquiry.treatment_completed)
        
        # Submit reciprocal reviews
        # 1. Patient reviews Hospital
        self.client.login(username='patient1', password='password123')
        response = self.client.post(
            reverse('submit_review', args=[self.inquiry.uuid]),
            {'rating': '5', 'comment': 'Excellent doctor'}
        )
        self.assertEqual(Review.objects.filter(inquiry=self.inquiry).count(), 1)
        
        # 2. Hospital reviews Patient
        self.client.login(username='hospital1', password='password123')
        response = self.client.post(
            reverse('submit_patient_review', args=[self.inquiry.uuid]),
            {'rating': '4', 'comment': 'Very polite patient'}
        )
        self.assertEqual(PatientReview.objects.filter(inquiry=self.inquiry).count(), 1)
        
        # Admin sends commission payment link
        self.client.login(username='admin1', password='password123')
        response = self.client.post(reverse('send_commission_link', args=[self.inquiry.uuid]))
        self.inquiry.refresh_from_db()
        self.assertTrue(self.inquiry.commission_payment_link_sent)
        
        # Hospital pays commission
        self.client.login(username='hospital1', password='password123')
        response = self.client.post(reverse('pay_commission', args=[self.inquiry.uuid]))
        self.inquiry.refresh_from_db()
        self.assertTrue(self.inquiry.commission_paid)
