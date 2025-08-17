#!/usr/bin/env python3
"""
Sysrai Platform Automated Testing Suite
Uses Playwright for end-to-end testing of all platform features
"""

import asyncio
import json
import os
import time
from datetime import datetime
from typing import Dict, List
import pytest
from playwright.async_api import async_playwright, Page, BrowserContext
import requests

class SysraiTestSuite:
    """Comprehensive testing suite for Sysrai platform"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.test_results = []
        self.test_user = {
            "email": f"test_user_{int(time.time())}@example.com",
            "password": "TestPassword123!",
            "name": "Test User"
        }
    
    async def run_full_test_suite(self):
        """Run complete test suite"""
        
        print("="*60)
        print("SYSRAI PLATFORM - AUTOMATED TEST SUITE")
        print("="*60)
        
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=False)  # Set to True for CI
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                # Core platform tests
                await self.test_health_endpoint(page)
                await self.test_user_registration(page)
                await self.test_user_login(page)
                await self.test_dashboard_access(page)
                
                # Film creation workflow
                await self.test_script_generation(page)
                await self.test_storyboard_creation(page)
                await self.test_video_generation(page)
                await self.test_film_assembly(page)
                
                # Advanced features
                await self.test_format_conversion(page)
                await self.test_ad_insertion(page)
                await self.test_film_splitting(page)
                await self.test_language_localization(page)
                
                # Business features
                await self.test_payment_system(page)
                await self.test_subscription_management(page)
                await self.test_usage_analytics(page)
                
                # Performance tests
                await self.test_concurrent_users()
                await self.test_large_file_handling(page)
                
                # Security tests
                await self.test_authentication_security(page)
                await self.test_data_isolation(page)
                
            finally:
                await browser.close()
        
        # Generate test report
        self.generate_test_report()
    
    async def test_health_endpoint(self, page: Page):
        """Test basic API health"""
        test_name = "Health Endpoint Test"
        
        try:
            response = requests.get(f"{self.base_url}/health")
            assert response.status_code == 200
            
            health_data = response.json()
            assert "status" in health_data
            
            self.log_test_result(test_name, "PASS", "Health endpoint responding correctly")
            
        except Exception as e:
            self.log_test_result(test_name, "FAIL", str(e))
    
    async def test_user_registration(self, page: Page):
        """Test user registration flow"""
        test_name = "User Registration"
        
        try:
            await page.goto(f"{self.base_url}/register")
            
            # Fill registration form
            await page.fill('input[name="email"]', self.test_user["email"])
            await page.fill('input[name="password"]', self.test_user["password"])
            await page.fill('input[name="confirm_password"]', self.test_user["password"])
            await page.fill('input[name="name"]', self.test_user["name"])
            
            # Submit form
            await page.click('button[type="submit"]')
            
            # Wait for redirect to dashboard
            await page.wait_for_url("**/dashboard")
            
            # Check for welcome message
            welcome_element = await page.wait_for_selector('.welcome-message')
            assert welcome_element is not None
            
            self.log_test_result(test_name, "PASS", "User registration successful")
            
        except Exception as e:
            self.log_test_result(test_name, "FAIL", str(e))
    
    async def test_user_login(self, page: Page):
        """Test user login functionality"""
        test_name = "User Login"
        
        try:
            # Logout first
            await page.goto(f"{self.base_url}/logout")
            
            # Go to login page
            await page.goto(f"{self.base_url}/login")
            
            # Fill login form
            await page.fill('input[name="email"]', self.test_user["email"])
            await page.fill('input[name="password"]', self.test_user["password"])
            
            # Submit form
            await page.click('button[type="submit"]')
            
            # Wait for dashboard
            await page.wait_for_url("**/dashboard")
            
            self.log_test_result(test_name, "PASS", "User login successful")
            
        except Exception as e:
            self.log_test_result(test_name, "FAIL", str(e))
    
    async def test_dashboard_access(self, page: Page):
        """Test dashboard functionality"""
        test_name = "Dashboard Access"
        
        try:
            await page.goto(f"{self.base_url}/dashboard")
            
            # Check for key dashboard elements
            await page.wait_for_selector('.credits-balance')
            await page.wait_for_selector('.create-project-btn')
            await page.wait_for_selector('.recent-projects')
            
            # Check credits display
            credits_text = await page.text_content('.credits-balance')
            assert "credits" in credits_text.lower()
            
            self.log_test_result(test_name, "PASS", "Dashboard loaded correctly")
            
        except Exception as e:
            self.log_test_result(test_name, "FAIL", str(e))
    
    async def test_script_generation(self, page: Page):
        """Test AI script generation"""
        test_name = "Script Generation"
        
        try:
            # Navigate to create project
            await page.click('.create-project-btn')
            await page.wait_for_url("**/create-project")
            
            # Fill project details
            await page.fill('input[name="title"]', "Test Film Project")
            await page.select_option('select[name="genre"]', "action")
            await page.fill('input[name="duration"]', "30")
            
            # Add source content
            source_content = """
            A story about a brave explorer who discovers a hidden treasure
            in an ancient temple. The explorer must overcome dangerous traps
            and solve puzzles to reach the treasure chamber.
            """
            await page.fill('textarea[name="source_content"]', source_content)
            
            # Generate script
            await page.click('button[data-action="generate-script"]')
            
            # Wait for script generation
            await page.wait_for_selector('.script-output', timeout=60000)
            
            # Verify script content
            script_text = await page.text_content('.script-output')
            assert len(script_text) > 100  # Ensure substantial content
            assert "scene" in script_text.lower()  # Should contain scene directions
            
            self.log_test_result(test_name, "PASS", "Script generated successfully")
            
        except Exception as e:
            self.log_test_result(test_name, "FAIL", str(e))
    
    async def test_storyboard_creation(self, page: Page):
        """Test storyboard generation"""
        test_name = "Storyboard Creation"
        
        try:
            # Click generate storyboard button
            await page.click('button[data-action="generate-storyboard"]')
            
            # Wait for storyboard panels
            await page.wait_for_selector('.storyboard-panel', timeout=60000)
            
            # Check number of panels
            panels = await page.query_selector_all('.storyboard-panel')
            assert len(panels) >= 3  # Should have multiple panels
            
            # Check panel content
            first_panel = panels[0]
            panel_text = await first_panel.text_content()
            assert len(panel_text) > 20  # Should have description
            
            self.log_test_result(test_name, "PASS", f"Storyboard created with {len(panels)} panels")
            
        except Exception as e:
            self.log_test_result(test_name, "FAIL", str(e))
    
    async def test_video_generation(self, page: Page):
        """Test video generation process"""
        test_name = "Video Generation"
        
        try:
            # Start video generation
            await page.click('button[data-action="generate-video"]')
            
            # Wait for generation to start
            await page.wait_for_selector('.generation-progress', timeout=10000)
            
            # Monitor progress (this will take several minutes)
            max_wait_time = 1800  # 30 minutes max
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                # Check if generation completed
                try:
                    completed_element = await page.wait_for_selector(
                        '.generation-complete', 
                        timeout=30000
                    )
                    if completed_element:
                        break
                except:
                    # Continue waiting
                    pass
                
                # Check progress
                progress_text = await page.text_content('.generation-progress')
                print(f"Video generation progress: {progress_text}")
                
                await asyncio.sleep(30)
            
            # Verify video was generated
            video_element = await page.query_selector('video[src*=".mp4"]')
            assert video_element is not None
            
            self.log_test_result(test_name, "PASS", "Video generated successfully")
            
        except Exception as e:
            self.log_test_result(test_name, "FAIL", str(e))
    
    async def test_film_assembly(self, page: Page):
        """Test final film assembly"""
        test_name = "Film Assembly"
        
        try:
            # Click assemble film button
            await page.click('button[data-action="assemble-film"]')
            
            # Wait for assembly process
            await page.wait_for_selector('.assembly-complete', timeout=300000)  # 5 minutes
            
            # Check for download link
            download_link = await page.query_selector('a[download*=".mp4"]')
            assert download_link is not None
            
            # Verify file size (should be substantial)
            href = await download_link.get_attribute('href')
            if href.startswith('http'):
                response = requests.head(href)
                content_length = int(response.headers.get('content-length', 0))
                assert content_length > 1000000  # At least 1MB
            
            self.log_test_result(test_name, "PASS", "Film assembled successfully")
            
        except Exception as e:
            self.log_test_result(test_name, "FAIL", str(e))
    
    async def test_format_conversion(self, page: Page):
        """Test different format outputs"""
        test_name = "Format Conversion"
        
        try:
            # Test TikTok format
            await page.click('button[data-format="tiktok"]')
            await page.wait_for_selector('.format-tiktok-ready', timeout=120000)
            
            # Test YouTube Shorts format
            await page.click('button[data-format="youtube-shorts"]')
            await page.wait_for_selector('.format-youtube-ready', timeout=120000)
            
            # Test Instagram Reels format
            await page.click('button[data-format="instagram-reels"]')
            await page.wait_for_selector('.format-instagram-ready', timeout=120000)
            
            self.log_test_result(test_name, "PASS", "All format conversions successful")
            
        except Exception as e:
            self.log_test_result(test_name, "FAIL", str(e))
    
    async def test_ad_insertion(self, page: Page):
        """Test advertisement insertion"""
        test_name = "Ad Insertion"
        
        try:
            await page.goto(f"{self.base_url}/dashboard/ads")
            
            # Upload test ad
            await page.set_input_files('input[type="file"]', 'test_ad.mp4')
            await page.click('button[data-action="upload-ad"]')
            
            # Insert ad into project
            await page.goto(f"{self.base_url}/project/{self.test_project_id}/ads")
            await page.click('button[data-action="insert-ad"]')
            
            # Verify ad insertion
            await page.wait_for_selector('.ad-inserted-success')
            
            self.log_test_result(test_name, "PASS", "Ad insertion successful")
            
        except Exception as e:
            self.log_test_result(test_name, "FAIL", str(e))
    
    async def test_film_splitting(self, page: Page):
        """Test film splitting for different platforms"""
        test_name = "Film Splitting"
        
        try:
            await page.click('button[data-action="split-film"]')
            
            # Select split points
            await page.click('.timeline-marker[data-time="300"]')  # 5 minutes
            await page.click('.timeline-marker[data-time="600"]')  # 10 minutes
            
            # Confirm split
            await page.click('button[data-action="confirm-split"]')
            
            # Wait for split completion
            await page.wait_for_selector('.split-complete', timeout=180000)
            
            # Verify multiple files created
            segments = await page.query_selector_all('.film-segment')
            assert len(segments) >= 2
            
            self.log_test_result(test_name, "PASS", f"Film split into {len(segments)} segments")
            
        except Exception as e:
            self.log_test_result(test_name, "FAIL", str(e))
    
    async def test_language_localization(self, page: Page):
        """Test multi-language support"""
        test_name = "Language Localization"
        
        try:
            await page.goto(f"{self.base_url}/project/{self.test_project_id}/localize")
            
            # Select target languages
            await page.check('input[value="spanish"]')
            await page.check('input[value="french"]')
            await page.check('input[value="german"]')
            
            # Start localization
            await page.click('button[data-action="start-localization"]')
            
            # Wait for completion
            await page.wait_for_selector('.localization-complete', timeout=600000)  # 10 minutes
            
            # Verify language versions
            language_tabs = await page.query_selector_all('.language-tab')
            assert len(language_tabs) >= 3
            
            self.log_test_result(test_name, "PASS", "Multi-language localization successful")
            
        except Exception as e:
            self.log_test_result(test_name, "FAIL", str(e))
    
    async def test_payment_system(self, page: Page):
        """Test payment integration"""
        test_name = "Payment System"
        
        try:
            await page.goto(f"{self.base_url}/billing")
            
            # Test credit purchase
            await page.click('button[data-package="medium"]')  # $49.99 package
            
            # Use Stripe test card
            await page.fill('input[name="cardNumber"]', '4242424242424242')
            await page.fill('input[name="expiryDate"]', '12/25')
            await page.fill('input[name="cvc"]', '123')
            await page.fill('input[name="billingName"]', 'Test User')
            
            # Submit payment
            await page.click('button[data-action="submit-payment"]')
            
            # Verify payment success
            await page.wait_for_selector('.payment-success')
            
            # Check credits updated
            await page.goto(f"{self.base_url}/dashboard")
            credits_text = await page.text_content('.credits-balance')
            assert "150" in credits_text  # Should show new credit balance
            
            self.log_test_result(test_name, "PASS", "Payment processing successful")
            
        except Exception as e:
            self.log_test_result(test_name, "FAIL", str(e))
    
    async def test_subscription_management(self, page: Page):
        """Test subscription features"""
        test_name = "Subscription Management"
        
        try:
            await page.goto(f"{self.base_url}/subscription")
            
            # Upgrade to Pro plan
            await page.click('button[data-plan="pro"]')
            
            # Confirm upgrade
            await page.click('button[data-action="confirm-upgrade"]')
            
            # Verify upgrade
            await page.wait_for_selector('.subscription-pro-active')
            
            self.log_test_result(test_name, "PASS", "Subscription upgrade successful")
            
        except Exception as e:
            self.log_test_result(test_name, "FAIL", str(e))
    
    async def test_usage_analytics(self, page: Page):
        """Test analytics dashboard"""
        test_name = "Usage Analytics"
        
        try:
            await page.goto(f"{self.base_url}/analytics")
            
            # Check for analytics widgets
            await page.wait_for_selector('.analytics-widget')
            
            # Verify charts are loaded
            charts = await page.query_selector_all('.chart-container')
            assert len(charts) >= 3
            
            # Check data points
            usage_text = await page.text_content('.usage
