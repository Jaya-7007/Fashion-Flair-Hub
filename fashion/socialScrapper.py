import json
import re
import http.client
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("SOCIAL_SCRAPPER_API_KEY")

def extract_hashtags(caption):
    """
    Extracts hashtags from a caption text.
    
    Args:
        caption (str): The caption text to extract hashtags from
    
    Returns:
        list: List of hashtags (without the # symbol)
    """
    if not caption:
        return []
    # Find all hashtags (words starting with #)
    hashtags = re.findall(r'#(\w+)', caption)
    return [tag.lower() for tag in hashtags]  # Convert to lowercase for consistent matching

def extract_video_urls_from_collector(og_data_dict):
    """
    Extracts video URLs from the 'collector' key in the API response.
    DEPRECATED: Used with the old API endpoint.
    """
    video_urls = []
    if 'collector' in og_data_dict and isinstance(og_data_dict['collector'], list):
        for post in og_data_dict['collector']:
            if 'video_url' in post and post['video_url']:
                video_urls.append(post['video_url'])
            if 'carousel_media' in post and isinstance(post['carousel_media'], list):
                for item in post['carousel_media']:
                    if 'video_url' in item and item['video_url']:
                        video_urls.append(item['video_url'])
    return video_urls

def extract_video_urls_from_sections(og_data_dict):
    """
    Extracts video URLs from the 'sections' key in the API response.
    DEPRECATED: Used with the old API endpoint.
    """
    video_urls = []
    try:
        sections = og_data_dict.get('data', {}).get('top', {}).get('sections', [])
        for section in sections:
            layout_content = section.get('layout_content', {})
            # For reels/clips
            one_by_two_item = layout_content.get('one_by_two_item', {})
            clips = one_by_two_item.get('clips', {}).get('items', [])
            for item in clips:
                media = item.get('media', {})
                video_versions = media.get('video_versions', [])
                if video_versions:
                    url = video_versions[0].get('url')
                    if url:
                        video_urls.append(url)
            # For regular media
            medias = layout_content.get('medias', [])
            for media_item in medias:
                media = media_item.get('media', {})
                video_versions = media.get('video_versions', [])
                if video_versions:
                    url = video_versions[0].get('url')
                    if url:
                        video_urls.append(url)
    except Exception as e:
        print(f"Error extracting from sections: {e}")
    return video_urls

def get_all_video_urls(og_data_dict):
    """
    Combines all extraction methods to get all video URLs from the API response.
    DEPRECATED: Used with the old API endpoint.
    """
    urls = set()
    urls.update(extract_video_urls_from_collector(og_data_dict))
    urls.update(extract_video_urls_from_sections(og_data_dict))
    return list(urls)

def get_instagram_reels_by_username(username):
    """
    Get Instagram reels for a specific username
    
    Args:
        username (str): Instagram username to fetch videos from
    
    Returns:
        list: List of video dictionaries with URLs, thumbnails, captions, and hashtags
    """
    print(f"\nFetching reels for Instagram user: @{username}")
    
    # Connect to Instagram API
    conn = http.client.HTTPSConnection("instagram-social-api.p.rapidapi.com")
    
    headers = {
        'x-rapidapi-key': "4a7319f197msh26e06ff8d5350c9p1469b4jsnf3b730dae82f",
        'x-rapidapi-host': "instagram-social-api.p.rapidapi.com"
    }
    
    # Make the request
    conn.request("GET", f"/v1/reels?username_or_id_or_url={username}", headers=headers)
    # print(conn.status)
    res = conn.getresponse()
    data = res.read()
    response_data = data.decode("utf-8")
    print(response_data)
    # Parse the response
    try:
        instagram_data = json.loads(response_data)
    except json.JSONDecodeError:
        print(f"Failed to parse JSON response for {username}")
        return []
    
    # Extract all videos with their hashtags
    videos_with_hashtags = []
    
    if "data" in instagram_data and "items" in instagram_data["data"]:
        print(f"Found {len(instagram_data['data']['items'])} items for {username}")
        
        for item in instagram_data["data"]["items"]:
            video_info = {
                "video_url": None,
                "thumbnail_url": None,
                "caption": "",
                "hashtags": []
            }
            
            # Get video URL
            if "video_versions" in item and len(item["video_versions"]) > 0:
                video_url = item["video_versions"][0]["url"]
                video_info["video_url"] = video_url
                print(f"Video URL: {video_url}")
            
            # Get thumbnail
            if "image_versions2" in item and "candidates" in item["image_versions2"]:
                if len(item["image_versions2"]["candidates"]) > 0:
                    video_info["thumbnail_url"] = item["image_versions2"]["candidates"][0]["url"]
            
            # Get caption and extract hashtags
            if "caption" in item and item["caption"] and "text" in item["caption"]:
                caption_text = item["caption"]["text"]
                video_info["caption"] = caption_text
                hashtags = extract_hashtags(caption_text)
                video_info["hashtags"] = hashtags
                print(f"Hashtags: {', '.join(['#'+tag for tag in hashtags])}")
            
            # Only add videos that have a URL
            if video_info["video_url"]:
                videos_with_hashtags.append(video_info)
                print(f"Added video for {username} with {len(video_info['hashtags'])} hashtags")
    else:
        print(f"No valid data structure found in response for {username}")
    
    print(f"Total videos fetched for {username}: {len(videos_with_hashtags)}")
    return videos_with_hashtags

def filter_videos_by_hashtags(videos, required_hashtags):
    """
    Filter videos to include those that contain substring matches of the required hashtags.
    
    Args:
        videos (list): List of video dictionaries with 'hashtags' key
        required_hashtags (list): List of hashtags to filter by (with or without # symbol)
    
    Returns:
        list: List of filtered videos
    """
    required_hashtags = [tag.lower().strip('#') for tag in required_hashtags]  # Normalize hashtags
    
    filtered_videos = []
    for video in videos:
        video_hashtags = [tag.lower() for tag in video.get('hashtags', [])]
        
        # For each required hashtag, check if it's a substring of any of the video's hashtags
        all_matches = True
        for req_tag in required_hashtags:
            # Check if any of the video's hashtags contain the required hashtag as a substring
            match_found = False
            matching_tags = []
            
            for video_tag in video_hashtags:
                if req_tag in video_tag:  # Substring match
                    match_found = True
                    matching_tags.append(video_tag)
            
            if match_found:
                # Store the matched tags in the video info for later reference
                if 'matching_tags' not in video:
                    video['matching_tags'] = {}
                video['matching_tags'][req_tag] = matching_tags
            else:
                all_matches = False
                break
        
        if all_matches:
            # Print which tags matched for debugging
            print(f"Video matched with hashtags:")
            for req_tag, matches in video.get('matching_tags', {}).items():
                print(f"  - Required '{req_tag}' matched with: {', '.join(['#'+tag for tag in matches])}")
                
            filtered_videos.append(video)
    
    return filtered_videos

def get_instagram_reels_by_username_and_hashtags(username, filter_hashtags=None):
    """
    Get Instagram reels for a username and filter by hashtags
    
    Args:
        username (str): Instagram username to fetch videos from
        filter_hashtags (list): List of hashtags to filter by (optional)
    
    Returns:
        list: List of filtered video dictionaries
    """
    # Get all videos for the username
    videos = get_instagram_reels_by_username(username)
    
    # Filter by hashtags if specified
    if filter_hashtags and videos:
        return filter_videos_by_hashtags(videos, filter_hashtags)
    
    return videos

def analyze_image_with_gemini(image_file):
    # Import from Django settings
    from django.conf import settings
    
    import google.generativeai as genai
    from PIL import Image
    
    # Configure API key from settings
    # genai.configure(api_key='AIzaSyDp0CWrFw-l5TdkwynD5rPRAKTgS7ot_AE')
   # client = genai.Client(api_key="AIzaSyDp0CWrFw-l5TdkwynD5rPRAKTgS7ot_AE")      THIS 
    
    # Set up the model
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    # Read and process the image
    img = Image.open(image_file)
    
    # Prepare the prompt
    prompt = """
    Analyze this fashion image and extract relevant keywords that describe:
    1. The type of clothing/outfit
    2. Colors and patterns
    3. Style categories (e.g., casual, formal, streetwear)
    4. Any notable fashion elements or accessories
    
    Return only the keywords as a comma-separated list, with no explanations.
    Focus on fashion-specific terminology that would be used as hashtags.
    """
    
    response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=prompt,
    )
    
    # Generate content with the image and prompt
    response = model.generate_content([prompt, img])
    
    # Extract and process keywords
    keywords_text = response.text.strip()
    keywords = [kw.strip().lower() for kw in keywords_text.split(',')]
    
    # Remove any '#' symbols if present
    keywords = [kw.strip('#') for kw in keywords]
    
    # Filter out very short keywords
    keywords = [kw for kw in keywords if len(kw) > 2]
    
    print(f"Extracted keywords from image: {keywords}")
    return keywords
