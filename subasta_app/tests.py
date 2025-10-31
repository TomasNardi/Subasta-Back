from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import Auction, WhatsAppGroup, Rule, Item
from datetime import datetime, timezone


class AuctionCreationFlowTestCase(APITestCase):
    """Test the complete auction creation flow"""

    def setUp(self):
        """Set up test user and client"""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_step1_create_auction_without_wa_group(self):
        """Test Step 1: Create basic auction without WhatsApp group"""
        data = {
            'title': 'Subasta Piezas Raras',
            'description': 'Cartas únicas y promos.',
            'claim_keyword': 'claim'
        }
        response = self.client.post('/api/auctions/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'Subasta Piezas Raras')
        self.assertEqual(response.data['claim_keyword'], 'claim')
        self.assertIsNone(response.data['wa_group'])

    def test_step1_create_auction_with_default_claim_keyword(self):
        """Test creating auction without claim_keyword uses default 'claim'"""
        data = {
            'title': 'Subasta Test',
            'description': 'Test auction'
        }
        response = self.client.post('/api/auctions/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['claim_keyword'], 'claim')

    def test_step1_create_auction_with_empty_claim_keyword(self):
        """Test creating auction with empty claim_keyword uses default 'claim'"""
        data = {
            'title': 'Subasta Test',
            'description': 'Test auction',
            'claim_keyword': ''
        }
        response = self.client.post('/api/auctions/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['claim_keyword'], 'claim')

    def test_step1_create_auction_with_custom_claim_keyword(self):
        """Test creating auction with custom claim_keyword"""
        data = {
            'title': 'Subasta Test',
            'description': 'Test auction',
            'claim_keyword': 'mio'
        }
        response = self.client.post('/api/auctions/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['claim_keyword'], 'mio')

    def test_step2_add_items_to_auction(self):
        """Test Step 2: Add items to an auction"""
        # Create auction first
        auction = Auction.objects.create(
            title='Test Auction',
            description='Test'
        )
        
        # Add item
        data = {
            'auction': auction.id,
            'name': 'Charizard holo',
            'base_price': '5000.00'
        }
        response = self.client.post('/api/items/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Charizard holo')
        self.assertEqual(response.data['auction'], auction.id)

    def test_step3_add_rules_to_auction(self):
        """Test Step 3: Add rules to an auction"""
        # Create auction first
        auction = Auction.objects.create(
            title='Test Auction',
            description='Test'
        )
        
        # Add rules
        data = {
            'rules': [
                'No ofertas fantasma. Oferta ganada = oferta pagada.',
                'Tenés 5 minutos para reclamar el item.',
                'El pago es inmediato por transferencia.'
            ]
        }
        response = self.client.post(f'/api/auctions/{auction.id}/rules/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['auction_id'], auction.id)
        self.assertEqual(len(response.data['created_rules']), 3)
        
        # Verify rules were created with correct keys
        rules = Rule.objects.filter(auction=auction).order_by('key')
        self.assertEqual(rules.count(), 3)
        self.assertEqual(rules[0].key, 'RULE_1')
        self.assertEqual(rules[1].key, 'RULE_2')
        self.assertEqual(rules[2].key, 'RULE_3')

    def test_step3_add_more_rules_increments_index(self):
        """Test adding more rules increments the index correctly"""
        auction = Auction.objects.create(
            title='Test Auction',
            description='Test'
        )
        
        # Add first batch of rules
        data = {'rules': ['Regla 1', 'Regla 2']}
        self.client.post(f'/api/auctions/{auction.id}/rules/', data, format='json')
        
        # Add second batch of rules
        data = {'rules': ['Regla 3', 'Regla 4']}
        response = self.client.post(f'/api/auctions/{auction.id}/rules/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify all rules have correct indices
        rules = Rule.objects.filter(auction=auction).order_by('key')
        self.assertEqual(rules.count(), 4)
        self.assertEqual(rules[0].key, 'RULE_1')
        self.assertEqual(rules[1].key, 'RULE_2')
        self.assertEqual(rules[2].key, 'RULE_3')
        self.assertEqual(rules[3].key, 'RULE_4')

    def test_step4_create_whatsapp_group(self):
        """Test Step 4: Create a WhatsApp group"""
        data = {
            'group_name': 'Cartas Premium Octubre',
            'group_id': '12093812903812-123@g.us'
        }
        response = self.client.post('/api/whatsapp-groups/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Cartas Premium Octubre')
        self.assertEqual(response.data['wa_chat_id'], '12093812903812-123@g.us')

    def test_step4_create_whatsapp_group_with_legacy_fields(self):
        """Test creating WhatsApp group with legacy field names"""
        data = {
            'name': 'Test Group',
            'wa_chat_id': '123456@g.us'
        }
        response = self.client.post('/api/whatsapp-groups/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Test Group')
        self.assertEqual(response.data['wa_chat_id'], '123456@g.us')

    def test_step5_assign_group_to_auction(self):
        """Test Step 5: Assign WhatsApp group to auction"""
        # Create auction and group
        auction = Auction.objects.create(
            title='Test Auction',
            description='Test'
        )
        wa_group = WhatsAppGroup.objects.create(
            wa_chat_id='123456@g.us',
            name='Test Group'
        )
        
        # Assign group to auction
        data = {'wa_group_id': wa_group.id}
        response = self.client.patch(f'/api/auctions/{auction.id}/assign-group/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['wa_group']['id'], wa_group.id)
        
        # Verify auction was updated
        auction.refresh_from_db()
        self.assertEqual(auction.wa_group.id, wa_group.id)

    def test_step5_assign_nonexistent_group_fails(self):
        """Test assigning non-existent group fails"""
        auction = Auction.objects.create(
            title='Test Auction',
            description='Test'
        )
        
        data = {'wa_group_id': 9999}
        response = self.client.patch(f'/api/auctions/{auction.id}/assign-group/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_complete_flow(self):
        """Test the complete auction creation flow end-to-end"""
        # Step 1: Create auction
        auction_data = {
            'title': 'Subasta Completa',
            'description': 'Test de flujo completo',
            'claim_keyword': 'reclamar'
        }
        response = self.client.post('/api/auctions/', auction_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        auction_id = response.data['id']
        
        # Step 2: Add items
        item_data = {
            'auction': auction_id,
            'name': 'Item Test',
            'base_price': '1000.00'
        }
        response = self.client.post('/api/items/', item_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Step 3: Add rules
        rules_data = {
            'rules': ['Regla 1', 'Regla 2', 'Regla 3']
        }
        response = self.client.post(f'/api/auctions/{auction_id}/rules/', rules_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Step 4: Create WhatsApp group
        group_data = {
            'group_name': 'Grupo Test',
            'group_id': 'test@g.us'
        }
        response = self.client.post('/api/whatsapp-groups/', group_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        group_id = response.data['id']
        
        # Step 5: Assign group to auction
        assign_data = {'wa_group_id': group_id}
        response = self.client.patch(f'/api/auctions/{auction_id}/assign-group/', assign_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify everything
        auction = Auction.objects.get(id=auction_id)
        self.assertEqual(auction.title, 'Subasta Completa')
        self.assertEqual(auction.claim_keyword, 'reclamar')
        self.assertEqual(auction.items.count(), 1)
        self.assertEqual(auction.rules.count(), 3)
        self.assertEqual(auction.wa_group.id, group_id)
