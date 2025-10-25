"""
Service for extracting recipes using Google Gemini AI.
"""
import os
import logging
import json
from typing import Optional, Dict, Any, Tuple
import requests
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
from io import BytesIO

# Try to import google.generativeai, but handle gracefully if not available
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    genai = None
    HAS_GEMINI = False
    logging.getLogger(__name__).warning("google.generativeai not installed. Gemini features will be disabled.")

logger = logging.getLogger(__name__)


class GeminiRecipeExtractor:
    """Extract recipes from various sources using Gemini AI."""
    
    def __init__(self):
        """Initialize the Gemini client."""
        if not HAS_GEMINI:
            logger.warning("google.generativeai module not available")
            self.client = None
            return
        
        self.api_key = os.environ.get('GOOGLE_GEMINI_API_KEY')
        if not self.api_key:
            logger.warning("GOOGLE_GEMINI_API_KEY not set in environment")
            self.client = None
        else:
            try:
                self.client = genai.Client(api_key=self.api_key)
                logger.info("Gemini client initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing Gemini client: {str(e)}")
                self.client = None
    
    def is_configured(self) -> bool:
        """Check if Gemini API is configured."""
        return self.client is not None
    
    def extract_from_url(self, url: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Extract recipe from a URL.
        Returns (success, recipe_data, error_message)
        """
        if not self.is_configured():
            return False, None, "Gemini API is not configured. Please set GOOGLE_GEMINI_API_KEY environment variable."
        
        try:
            logger.info(f"Fetching recipe from URL: {url}")
            
            # Fetch the webpage
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try to find structured recipe data (JSON-LD) first
            structured_data = self._extract_structured_recipe_data(soup)
            if structured_data:
                logger.info("Found structured recipe data (JSON-LD)")
                text_content = structured_data
            else:
                # Fallback to text extraction
                logger.info("No structured data found, using text extraction")
                
                # Remove script and style elements
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.decompose()
                
                # Get text
                text_content = soup.get_text(separator='\n', strip=True)
                
                # Limit the text length to avoid token limits (approx 100k chars)
                if len(text_content) > 100000:
                    text_content = text_content[:100000]
            
            # Extract recipe using Gemini
            recipe_data = self._extract_recipe_with_gemini(text_content, url)
            
            if recipe_data:
                # Add the URL as the source
                if 'source' not in recipe_data or not recipe_data['source']:
                    recipe_data['source'] = {}
                recipe_data['source']['url'] = url
                
                # Auto-populate source name with the URL
                if not recipe_data['source'].get('name'):
                    recipe_data['source']['name'] = url
                
                logger.info(f"Successfully extracted recipe from URL: {url}")
                return True, recipe_data, None
            else:
                return False, None, "Could not extract recipe from the webpage."
        
        except requests.RequestException as e:
            error_msg = f"Error fetching URL: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
        except Exception as e:
            error_msg = f"Error extracting recipe from URL: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
    
    def extract_from_text(self, text_content: str, filename: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Extract recipe from plain text.
        Returns (success, recipe_data, error_message)
        """
        if not self.is_configured():
            return False, None, "Gemini API is not configured. Please set GOOGLE_GEMINI_API_KEY environment variable."
        
        try:
            logger.info(f"Extracting recipe from text (filename: {filename})")
            
            # Extract recipe using Gemini
            recipe_data = self._extract_recipe_with_gemini(text_content, None)
            
            if recipe_data:
                # Add filename as source if provided
                if filename:
                    if 'source' not in recipe_data or not recipe_data['source']:
                        recipe_data['source'] = {}
                    if not recipe_data['source'].get('name'):
                        recipe_data['source']['name'] = filename
                
                logger.info("Successfully extracted recipe from text")
                return True, recipe_data, None
            else:
                return False, None, "Could not extract recipe from the text."
        
        except Exception as e:
            error_msg = f"Error extracting recipe from text: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
    
    def extract_from_pdf(self, pdf_data: bytes, filename: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Extract recipe from PDF file.
        Returns (success, recipe_data, error_message)
        """
        if not self.is_configured():
            return False, None, "Gemini API is not configured. Please set GOOGLE_GEMINI_API_KEY environment variable."
        
        try:
            logger.info(f"Extracting recipe from PDF (filename: {filename})")
            
            # Read PDF
            pdf_reader = PdfReader(BytesIO(pdf_data))
            
            # Extract text from all pages
            text_content = ""
            for page in pdf_reader.pages:
                text_content += page.extract_text() + "\n"
            
            if not text_content.strip():
                return False, None, "Could not extract text from PDF file."
            
            # Extract recipe using Gemini
            recipe_data = self._extract_recipe_with_gemini(text_content, None)
            
            if recipe_data:
                # Add filename as source if provided
                if filename:
                    if 'source' not in recipe_data or not recipe_data['source']:
                        recipe_data['source'] = {}
                    if not recipe_data['source'].get('name'):
                        recipe_data['source']['name'] = filename
                
                logger.info("Successfully extracted recipe from PDF")
                return True, recipe_data, None
            else:
                return False, None, "Could not extract recipe from the PDF."
        
        except Exception as e:
            error_msg = f"Error extracting recipe from PDF: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
    
    def _extract_structured_recipe_data(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Try to extract structured recipe data (JSON-LD) from the page.
        Returns formatted text if found, None otherwise.
        """
        try:
            # Look for JSON-LD script tags with recipe data
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string)
                    
                    # Handle both single objects and arrays
                    if isinstance(data, list):
                        recipes = [item for item in data if item.get('@type') == 'Recipe']
                        if recipes:
                            data = recipes[0]
                    
                    # Check if this is a Recipe object
                    if data.get('@type') == 'Recipe':
                        logger.info("Found Recipe schema in JSON-LD")
                        
                        # Format the structured data as readable text for Gemini
                        formatted = []
                        formatted.append(f"RECIPE: {data.get('name', 'Unknown')}\n")
                        
                        if data.get('description'):
                            formatted.append(f"DESCRIPTION: {data.get('description')}\n")
                        
                        if data.get('author'):
                            author = data['author']
                            if isinstance(author, dict):
                                formatted.append(f"AUTHOR: {author.get('name', '')}\n")
                            else:
                                formatted.append(f"AUTHOR: {author}\n")
                        
                        # Extract ingredients
                        ingredients = data.get('recipeIngredient', [])
                        if ingredients:
                            formatted.append("\nINGREDIENTS:")
                            for ing in ingredients:
                                formatted.append(f"- {ing}")
                            formatted.append("")
                        
                        # Extract instructions
                        instructions = data.get('recipeInstructions', [])
                        if instructions:
                            formatted.append("\nINSTRUCTIONS:")
                            if isinstance(instructions, str):
                                formatted.append(instructions)
                            elif isinstance(instructions, list):
                                for i, step in enumerate(instructions, 1):
                                    if isinstance(step, dict):
                                        text = step.get('text', '')
                                        if text:
                                            formatted.append(f"{i}. {text}")
                                    elif isinstance(step, str):
                                        formatted.append(f"{i}. {step}")
                            formatted.append("")
                        
                        # Extract additional info
                        if data.get('recipeYield'):
                            formatted.append(f"\nYIELD: {data.get('recipeYield')}")
                        
                        if data.get('totalTime'):
                            formatted.append(f"TOTAL TIME: {data.get('totalTime')}")
                        
                        if data.get('recipeCategory'):
                            formatted.append(f"CATEGORY: {data.get('recipeCategory')}")
                        
                        if data.get('recipeCuisine'):
                            formatted.append(f"CUISINE: {data.get('recipeCuisine')}")
                        
                        if data.get('keywords'):
                            formatted.append(f"KEYWORDS: {data.get('keywords')}")
                        
                        return '\n'.join(formatted)
                
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    logger.debug(f"Error parsing JSON-LD: {str(e)}")
                    continue
            
            return None
        
        except Exception as e:
            logger.error(f"Error extracting structured data: {str(e)}")
            return None
    
    def _extract_recipe_with_gemini(self, content: str, source_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Use Gemini to extract recipe data from content.
        Returns recipe data in JSON format or None if extraction fails.
        """
        if not self.client:
            logger.error("Gemini client not initialized")
            return None
        
        try:
            # Create the prompt
            prompt = self._create_extraction_prompt(content, source_url)
            
            # Call Gemini API
            response = self.client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,  # Low temperature for more deterministic output
                    max_output_tokens=8192,
                )
            )
            
            # Extract the response text
            response_text = response.text.strip()
            logger.debug(f"Gemini response: {response_text[:500]}...")
            
            # Try to parse JSON from the response
            recipe_data = self._parse_json_response(response_text)
            
            if recipe_data:
                # Validate basic structure
                if self._validate_recipe_data(recipe_data):
                    return recipe_data
                else:
                    logger.error("Invalid recipe data structure from Gemini")
                    return None
            else:
                logger.error("Could not parse JSON from Gemini response")
                return None
        
        except Exception as e:
            logger.error(f"Error calling Gemini API: {str(e)}")
            return None
    
    def _create_extraction_prompt(self, content: str, source_url: Optional[str] = None) -> str:
        """Create the prompt for Gemini to extract recipe data."""
        prompt = f"""Extract the recipe information from the following content and return it as a JSON object.

The JSON should have this exact structure:
{{
  "name": "Recipe name",
  "ingredients": [
    {{
      "amount": "amount (e.g., 2, 1/2, 1.5)",
      "unit": "unit (e.g., cups, oz, tsp)",
      "description": "ingredient description"
    }}
  ],
  "instructions": "Step-by-step cooking instructions with each step numbered or separated by blank lines",
  "notes": "Any additional notes or tips",
  "tags": ["tag1", "tag2"],
  "source": {{
    "name": "Source name (e.g., blog name, cookbook title, author name)",
    "url": "{source_url if source_url else ''}",
    "author": "Recipe author if mentioned",
    "issue": "Issue or edition if from a magazine/publication"
  }}
}}

Important guidelines:
1. Extract ALL ingredients with amounts, units, and descriptions where available
2. If amount or unit is not specified, use empty string ""
3. For instructions: PRESERVE the original formatting and numbering if present (e.g., 1., 2., 3.)
4. If instructions are NOT numbered, format them with numbered steps (1., 2., 3., etc.) OR separate each step with blank lines
5. Each instruction step should be clear and distinct
6. Extract any notes, tips, or additional information into the "notes" field
7. Infer appropriate tags (e.g., "DESSERT", "VEGETARIAN", "QUICK", "ITALIAN")
8. For source.name: try to extract the website/blog name, cookbook title, or publication name
9. If source name cannot be determined, leave it as empty string "" (it will be auto-filled with the URL)
10. Make all tags uppercase
11. Return ONLY the JSON object, no additional text or explanation

Content to extract from:
{content}

Return the recipe as JSON:"""
        
        return prompt
    
    def _parse_json_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from Gemini response, handling various formats."""
        try:
            # Try direct JSON parse
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            if "```json" in response_text:
                start_idx = response_text.find("```json") + 7
                end_idx = response_text.find("```", start_idx)
                if end_idx != -1:
                    json_str = response_text[start_idx:end_idx].strip()
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        pass
            
            # Try to extract JSON from regular code blocks
            if "```" in response_text:
                start_idx = response_text.find("```") + 3
                end_idx = response_text.find("```", start_idx)
                if end_idx != -1:
                    json_str = response_text[start_idx:end_idx].strip()
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        pass
            
            # Try to find JSON object in the text
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
            
            logger.error("Could not parse JSON from response")
            return None
    
    def _validate_recipe_data(self, recipe_data: Dict[str, Any]) -> bool:
        """Validate that recipe data has required fields."""
        required_fields = ['name', 'ingredients']
        
        for field in required_fields:
            if field not in recipe_data:
                logger.error(f"Missing required field: {field}")
                return False
        
        if not isinstance(recipe_data['ingredients'], list):
            logger.error("Ingredients must be a list")
            return False
        
        if len(recipe_data['ingredients']) == 0:
            logger.error("Recipe must have at least one ingredient")
            return False
        
        # Validate ingredient structure
        for i, ingredient in enumerate(recipe_data['ingredients']):
            if not isinstance(ingredient, dict):
                logger.error(f"Ingredient {i} must be a dictionary")
                return False
            if 'description' not in ingredient or not ingredient['description']:
                logger.error(f"Ingredient {i} must have a description")
                return False
        
        return True


# Create global instance
gemini_service = GeminiRecipeExtractor()

