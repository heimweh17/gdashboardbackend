"""
Gemini AI service for generating insights from analysis results.
"""
import json
import os
import re
from typing import Any, Dict

try:
	import google.generativeai as genai
	from google.generativeai.types import HarmCategory, HarmBlockThreshold
	GEMINI_AVAILABLE = True
except ImportError:
	GEMINI_AVAILABLE = False

from app.core.config import settings


def _get_available_models() -> list[str]:
	"""
	List available Gemini models for generateContent.
	Returns list of model names that support generateContent.
	"""
	if not GEMINI_AVAILABLE:
		return []
	
	if not settings.gemini_api_key:
		return []
	
	try:
		genai.configure(api_key=settings.gemini_api_key)
		models = genai.list_models()
		
		available = []
		for model in models:
			# Check if model supports generateContent
			if "generateContent" in model.supported_generation_methods:
				# Extract just the model name (remove 'models/' prefix if present)
				name = model.name
				if name.startswith("models/"):
					name = name[7:]  # Remove "models/" prefix
				available.append(name)
				# Also add with prefix for compatibility
				if not name.startswith("models/"):
					available.append(f"models/{name}")
		
		return available
	except Exception:
		return []


def _find_working_model(preferred: str) -> str:
	"""
	Find a working model by checking available models.
	Returns the preferred model if available, otherwise returns first available model.
	"""
	available = _get_available_models()
	
	if not available:
		# Fallback to common model names if list_models fails
		return preferred
	
	# Check if preferred model is available (with or without models/ prefix)
	preferred_variants = [preferred, f"models/{preferred}"]
	if preferred.startswith("models/"):
		preferred_variants = [preferred, preferred[7:]]
	
	for variant in preferred_variants:
		if variant in available:
			return variant
	
	# Return first available model
	return available[0] if available else preferred


def generate_insight(analysis_result: Dict[str, Any], context: Dict[str, Any] | None = None) -> Dict[str, Any]:
	"""
	Generate AI insight from analysis result using Gemini.
	
	Args:
		analysis_result: The analysis result dict (summary, grid_density, clustering)
		context: Optional context dict (city_name, filters, viewport_bbox)
	
	Returns:
		Dict with 'text', 'highlights', and 'method' keys
	"""
	if not GEMINI_AVAILABLE:
		raise RuntimeError("google-generativeai package not installed")
	
	if not settings.gemini_api_key:
		raise ValueError("GEMINI_API_KEY not configured")
	
	genai.configure(api_key=settings.gemini_api_key)
	
	# Find a working model by checking available models
	model_name = _find_working_model(settings.gemini_model)
	
	# Try to create model
	try:
		model = genai.GenerativeModel(
			model_name=model_name,
			safety_settings={
				HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
				HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
				HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
				HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
			},
		)
	except Exception as e:
		# If still fails, try fallback models
		fallback_models = ["gemini-1.5-pro", "gemini-1.0-pro", "gemini-pro"]
		model = None
		last_error = str(e)
		
		for fallback in fallback_models:
			try:
				# Try both with and without models/ prefix
				for variant in [fallback, f"models/{fallback}"]:
					try:
						model = genai.GenerativeModel(
							model_name=variant,
							safety_settings={
								HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
								HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
								HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
								HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
							},
						)
						model_name = variant
						break
					except Exception:
						continue
				if model:
					break
			except Exception:
				continue
		
		if model is None:
			available_models = _get_available_models()
			available_str = ", ".join(available_models[:5]) if available_models else "none found"
			raise RuntimeError(
				f"Failed to initialize Gemini model. Original error: {last_error}. "
				f"Tried: {settings.gemini_model}, {model_name}, and fallbacks. "
				f"Available models: {available_str}"
			)
	
	# Build prompt
	prompt = _build_prompt(analysis_result, context)
	
	# Generate response
	try:
		response = model.generate_content(
			prompt,
			generation_config={
				"temperature": 0.7,
				"max_output_tokens": max(settings.ai_max_output_tokens, 1000),  # Ensure at least 1000 tokens
			},
		)
	except Exception as e:
		raise RuntimeError(f"Failed to generate content from Gemini: {str(e)}")
	
	# Get full text response
	if not hasattr(response, 'text') or not response.text:
		raise RuntimeError("Empty response from Gemini model")
	
	# Get the complete response text
	# Handle cases where response might be truncated
	text = response.text.strip()
	
	# Check if response was truncated (Gemini sometimes returns incomplete JSON)
	# If the text doesn't end with }, try to get more
	if text.count('{') > text.count('}'):
		# JSON might be incomplete, but we'll try to parse what we have
		pass
	
	# Try to extract JSON if wrapped in markdown code blocks
	# Handle multiple formats: ```json, ```, or plain JSON
	json_text = text
	
	# Remove markdown code blocks
	if "```json" in text.lower():
		# Find all occurrences and get the largest JSON block
		parts = text.split("```json")
		if len(parts) > 1:
			# Take the part after ```json
			candidate = parts[1].split("```")[0].strip()
			if candidate.startswith("{") or candidate.startswith("["):
				json_text = candidate
	elif "```" in text:
		# Try to find JSON between code blocks
		parts = text.split("```")
		for i in range(1, len(parts), 2):  # Every odd index is inside code blocks
			candidate = parts[i].strip()
			# Remove language identifier if present
			if candidate.startswith("json"):
				candidate = candidate[4:].strip()
			if candidate.startswith("{") or candidate.startswith("["):
				json_text = candidate
				break
	
	# Try to find JSON object in the text if it's not already extracted
	if not (json_text.startswith("{") or json_text.startswith("[")):
		# Look for JSON object boundaries
		start_idx = json_text.find("{")
		if start_idx >= 0:
			# Find matching closing brace
			brace_count = 0
			end_idx = start_idx
			for i in range(start_idx, len(json_text)):
				if json_text[i] == "{":
					brace_count += 1
				elif json_text[i] == "}":
					brace_count -= 1
					if brace_count == 0:
						end_idx = i + 1
						break
			if end_idx > start_idx:
				json_text = json_text[start_idx:end_idx]
	
	# Parse JSON
	result = None
	try:
		result = json.loads(json_text)
	except json.JSONDecodeError as e:
		# If JSON parsing fails, try to manually extract fields
		# This handles cases where JSON might be incomplete or malformed
		
		# Try to extract text field - handle multi-line strings with proper quote matching
		text_value = None
		# Pattern 1: "text": "value" (handles escaped quotes)
		text_patterns = [
			r'"text"\s*:\s*"((?:[^"\\]|\\.|\\n)*)"',  # Double quotes with escapes
			r'"text"\s*:\s*"([^"]*)"',  # Simple double quotes
			r"'text'\s*:\s*'([^']*)'",  # Single quotes
		]
		
		for pattern in text_patterns:
			match = re.search(pattern, text, re.DOTALL)
			if match:
				text_value = match.group(1)
				# Unescape common escape sequences
				text_value = text_value.replace('\\n', '\n').replace('\\"', '"').replace("\\'", "'")
				break
		
		# Extract highlights array
		highlights = []
		highlights_pattern = r'"highlights"\s*:\s*\[(.*?)\]'
		highlights_match = re.search(highlights_pattern, text, re.DOTALL)
		if highlights_match:
			highlights_content = highlights_match.group(1)
			# Extract individual string values from array
			highlight_items = re.findall(r'"(?:[^"\\]|\\.)*"', highlights_content)
			for item in highlight_items:
				# Remove quotes and unescape
				clean_item = item[1:-1].replace('\\n', '\n').replace('\\"', '"')
				highlights.append(clean_item)
		
		# Extract method field
		method_value = None
		method_patterns = [
			r'"method"\s*:\s*"((?:[^"\\]|\\.)*)"',
			r'"method"\s*:\s*"([^"]*)"',
			r"'method'\s*:\s*'([^']*)'",
		]
		for pattern in method_patterns:
			match = re.search(pattern, text, re.DOTALL)
			if match:
				method_value = match.group(1).replace('\\n', '\n').replace('\\"', '"')
				break
		
		# Build result
		if text_value:
			result = {
				"text": text_value,
				"highlights": highlights if highlights else [],
				"method": method_value or "Gemini analysis based on provided data",
			}
		else:
			# Last resort: try to find any JSON-like structure and extract what we can
			# Look for the text field value even if JSON is malformed
			text_start = text.find('"text"')
			if text_start >= 0:
				# Find the colon after "text"
				colon_pos = text.find(':', text_start)
				if colon_pos >= 0:
					# Find the opening quote
					quote_start = text.find('"', colon_pos)
					if quote_start >= 0:
						# Find the closing quote, handling escaped quotes
						quote_end = quote_start + 1
						while quote_end < len(text):
							if text[quote_end] == '"' and text[quote_end - 1] != '\\':
								break
							quote_end += 1
						if quote_end < len(text):
							extracted_text = text[quote_start + 1:quote_end]
							result = {
								"text": extracted_text.replace('\\n', '\n').replace('\\"', '"'),
								"highlights": highlights if highlights else [],
								"method": method_value or "Gemini analysis based on provided data",
							}
			
			# Final fallback
			if not result:
				result = {
					"text": text.replace("```json", "").replace("```", "").strip(),
					"highlights": [],
					"method": "Gemini analysis based on provided data",
				}
	
	# Ensure required fields
	if "text" not in result:
		result["text"] = text
	if "highlights" not in result or not isinstance(result["highlights"], list):
		result["highlights"] = [result.get("text", text)[:100] + "..."]
	if "method" not in result:
		result["method"] = "Gemini analysis based on provided data"
	
	return result


def _build_prompt(analysis_result: Dict[str, Any], context: Dict[str, Any] | None = None) -> str:
	"""Build the prompt for Gemini."""
	
	summary = analysis_result.get("summary", {})
	clustering = analysis_result.get("clustering", {})
	grid = analysis_result.get("grid_density", {})
	
	# Extract key metrics
	total_points = summary.get("total_points", 0)
	category_counts = summary.get("category_counts", {})
	bbox = summary.get("bbox")
	mean_center = summary.get("mean_center")
	num_clusters = clustering.get("num_clusters", 0)
	num_noise = clustering.get("num_noise", 0)
	clusters = clustering.get("clusters", [])
	
	prompt_parts = [
		"You are a geospatial data analyst. Analyze the following geospatial analysis results and provide insights.",
		"",
		"CRITICAL RULES:",
		"1. DO NOT invent or make up any data. Only reference fields that are present in the analysis_result.",
		"2. Use hedging language: 'suggests', 'may indicate', 'appears to', 'likely', 'possibly'.",
		"3. Include numeric proportions when available (percentages, counts).",
		"4. If data is missing, explicitly state that limitation.",
		"",
		"ANALYSIS DATA:",
		f"- Total points: {total_points}",
	]
	
	if category_counts:
		# Sort by count and show top categories
		sorted_cats = sorted(category_counts.items(), key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0, reverse=True)
		prompt_parts.append("- Category distribution:")
		for cat, count in sorted_cats[:10]:  # Top 10
			pct = (count / total_points * 100) if total_points > 0 else 0
			prompt_parts.append(f"  * {cat}: {count} ({pct:.1f}%)")
	else:
		prompt_parts.append("- Category counts: Not available")
	
	if bbox:
		prompt_parts.append(f"- Bounding box: {json.dumps(bbox)}")
	
	if mean_center:
		prompt_parts.append(f"- Mean center: {json.dumps(mean_center)}")
	
	prompt_parts.append(f"- Clustering: {num_clusters} clusters, {num_noise} noise points")
	
	if clusters:
		largest = max(clusters, key=lambda c: c.get("size", 0), default=None)
		if largest:
			prompt_parts.append(f"- Largest cluster: size {largest.get('size', 0)} at {json.dumps(largest.get('centroid', {}))}")
	
	if context:
		if context.get("city_name"):
			prompt_parts.append(f"- Context: City: {context['city_name']}")
		if context.get("viewport_bbox"):
			prompt_parts.append(f"- Viewport: {json.dumps(context['viewport_bbox'])}")
	
	prompt_parts.extend([
		"",
		"OUTPUT FORMAT: Return ONLY a valid JSON object (no markdown, no code blocks, no explanations). The JSON must have exactly these fields:",
		"{",
		'  "text": "A concise scientific-style narrative paragraph (3-5 sentences) summarizing the spatial patterns, distribution characteristics, and notable findings. Use hedging language and reference specific numbers from the data.",',
		'  "highlights": ["Bullet point 1 with key finding and %", "Bullet point 2", "Bullet point 3"],',
		'  "method": "Brief note on methodology/assumptions (e.g., DBSCAN clustering, category field used, spatial extent)"',
		"}",
		"",
		"IMPORTANT: Return ONLY the JSON object, nothing else. No markdown code blocks, no explanations, just the raw JSON.",
		"",
		"Generate the insight now:",
	])
	
	return "\n".join(prompt_parts)

