from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.db.models import Q
import http.client
import json
import re
import requests
from itertools import chain
from google import genai
from PIL import Image
import io
from .socialScrapper import (
    get_instagram_reels_by_username,
    get_instagram_reels_by_username_and_hashtags,
    extract_hashtags
)

# Hard-coded list of fashion influencer usernames to scrape
FASHION_ACCOUNTS = [
    "aashistyling",
    "Meghansh07",
    "fits_withme",
    "linkforoutfits",
    "laxmi_shetty",
    "vouguemann",
    "menlifestylestudio",
    "mensoutfitsvision",
    "kikalateefff"
]

# Add these women fashion influencer accounts
WOMEN_FASHION_ACCOUNTS = [
     "aashistyling",
    "Meghansh07",
    "fits_withme",
    # "diipakhosla",
    # "masoom.minawala",
    # "stylebyami",
    # "thestylestate",
    # "aastha_gill",
    # "kritisanon"
]

# Add these men fashion influencer accounts in the constants section at the top
MEN_FASHION_ACCOUNTS = [
    "vouguemann",
    "menlifestylestudio", 
    "mensoutfitsvision",
    
    "menswithstreetstyle",
    "mensfashionreview",
    "thedapperedman",
    "menwithclass",
    "menwithstyle"
]

# Create your views here.
def searchVideo(request):
    return render(request, 'search.html')

def viewVideos(request):
    # Handle both GET and POST requests to support different search entry points
    hashtag = ''
    
    if request.method == 'POST':
        hashtag = request.POST.get('hashtag', '').strip()
    elif request.method == 'GET':
        hashtag = request.GET.get('hashtag', '').strip()
        
    # Clean the hashtag - remove # if present and any spaces
    if hashtag.startswith('#'):
        hashtag = hashtag[1:]
    
    # Replace spaces with underscores for proper API query
    hashtag = re.sub(r'\s+', '_', hashtag)
        
    if not hashtag:
        return render(request, 'result.html', {'error': 'Please provide a hashtag'})
    
    try:
        all_videos = []
        
        # Fetch videos from all hard-coded accounts
        for username in FASHION_ACCOUNTS:
            try:
                # Get reels for this username
                print(f"Fetching videos for {username}")
                user_videos = get_instagram_reels_by_username(username)
                print(f"Got {len(user_videos)} videos from {username}")
                
                # Add username to each video for display purposes
                for video in user_videos:
                    video['username'] = username
                
                all_videos.extend(user_videos)
            except Exception as e:
                # If one account fails, continue with others
                print(f"Error fetching videos from {username}: {e}")
                continue
        
        print(f"Total videos fetched from all accounts: {len(all_videos)}")
        
        # Collect and print all unique hashtags found across all videos
        all_hashtags = set()
        hashtag_counts = {}
        for video in all_videos:
            video_hashtags = video.get('hashtags', [])
            all_hashtags.update(video_hashtags)
            
            # Count frequency of each hashtag
            for tag in video_hashtags:
                if tag in hashtag_counts:
                    hashtag_counts[tag] += 1
                else:
                    hashtag_counts[tag] = 1
        
        # Sort hashtags by frequency (most common first)
        sorted_hashtags = sorted(hashtag_counts.items(), key=lambda x: x[1], reverse=True)
        
        print(f"\nAll hashtags found ({len(all_hashtags)}):")
        print("=" * 50)
        for tag, count in sorted_hashtags:
            print(f"#{tag}: {count} videos")
        print("=" * 50)
        
        # Filter videos by the hashtag - using substring matching
        filtered_videos = []
        search_hashtag = hashtag.lower()
        
        for video in all_videos:
            video_hashtags = [tag.lower() for tag in video.get('hashtags', [])]
            
            # Check if search_hashtag is a substring of any hashtag in this video
            matched_tags = []
            for tag in video_hashtags:
                if search_hashtag in tag:  # Substring match instead of exact match
                    matched_tags.append(tag)
            
            # If we found any matches, add the video to results
            if matched_tags:
                # Store the matched tags in the video info for reference in the template
                video['matching_tags'] = matched_tags
                filtered_videos.append(video)
                print(f"Video from @{video.get('username', 'unknown')} matched: {', '.join(['#'+tag for tag in matched_tags])}")

        print(f"Found {len(filtered_videos)} videos with hashtags containing '{search_hashtag}'")
        
        # Extract just the video URLs for backward compatibility with result.html
        video_urls = []
        for video in filtered_videos:
            if video.get('video_url'):
                video_urls.append(video['video_url'])
                print(f"Added URL: {video['video_url'][:50]}...")
        
        print(f"Final video URLs count: {len(video_urls)}")
        
        return render(request, 'result.html', {
            'videos': filtered_videos,
            'video_urls': video_urls,
            'hashtag': hashtag,
            'count': len(filtered_videos),
            'accounts_searched': FASHION_ACCOUNTS
        })
        
    except Exception as e:
        import traceback
        print(f"Error in viewVideos: {str(e)}")
        print(traceback.format_exc())
        return render(request, 'result.html', {'error': f'Error fetching videos: {str(e)}'})

def viewUserReels(request):
    """
    View to search for reels by username and optionally filter by hashtags
    """
    username = ''
    filter_hashtags = []
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        filter_hashtags_str = request.POST.get('hashtags', '').strip()
        if filter_hashtags_str:
            # Split by commas or spaces and remove any '#' characters
            filter_hashtags = [tag.strip('#') for tag in re.split(r'[,\s]+', filter_hashtags_str) if tag.strip('#')]
    elif request.method == 'GET':
        username = request.GET.get('username', '').strip()
        filter_hashtags_str = request.GET.get('hashtags', '').strip()
        if filter_hashtags_str:
            filter_hashtags = [tag.strip('#') for tag in re.split(r'[,\s]+', filter_hashtags_str) if tag.strip('#')]
        
    if not username:
        return render(request, 'user_reels.html', {'error': 'Please provide a username'})
    
    try:
        if filter_hashtags:
            videos = get_instagram_reels_by_username_and_hashtags(username, filter_hashtags)
            video_urls = [video['video_url'] for video in videos]
            return render(request, 'user_reels.html', {
                'username': username,
                'hashtags': filter_hashtags,
                'videos': videos,
                'video_urls': video_urls,  # For backward compatibility
                'count': len(videos),
                'filtered': True
            })
        else:
            videos = get_instagram_reels_by_username(username)
            video_urls = [video['video_url'] for video in videos]
            return render(request, 'user_reels.html', {
                'username': username,
                'videos': videos,
                'video_urls': video_urls,  # For backward compatibility
                'count': len(videos),
                'filtered': False
            })
        
    except Exception as e:
        return render(request, 'user_reels.html', {'error': f'Error fetching videos: {str(e)}'})

def proxy_video(request):
    url = request.GET.get('url')
    if not url:
        return HttpResponse("No URL provided", status=400)
    
    try:
        response = requests.get(url, stream=True)
        return HttpResponse(
            response.content,
            content_type=response.headers.get('content-type', 'video/mp4')
        )
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)

def image_search(request):
    """
    Search videos based on an uploaded image using Gemini API for image analysis
    """
    if request.method == 'POST' and request.FILES.get('image'):
        try:
            image_file = request.FILES['image']
            
            # Create temp directory if it doesn't exist
            import os
            temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'temp_uploads')
            os.makedirs(temp_dir, exist_ok=True)
            
            # Generate a unique filename
            import uuid
            file_extension = os.path.splitext(image_file.name)[1].lower()
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            temp_file_path = os.path.join(temp_dir, unique_filename)
            
            # Save the uploaded file to disk
            with open(temp_file_path, 'wb+') as destination:
                for chunk in image_file.chunks():
                    destination.write(chunk)
            
            print(f"Saved uploaded image to: {temp_file_path}")
            
            # Create base64 representation for display in template
            import base64
            from io import BytesIO
            from PIL import Image
            
            # Create base64 representation for display in template
            image = Image.open(temp_file_path)
            # Resize for performance if needed
            if max(image.size) > 800:
                image.thumbnail((800, 800))
            buffer = BytesIO()
            image.save(buffer, format="JPEG")
            image_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
            uploaded_image = f"data:image/jpeg;base64,{image_str}"
            
            # Continue with existing code...
            print(f"Analyzing image: {temp_file_path}")
            keywords = analyze_image_with_gemini(temp_file_path)
            
            if not keywords:
                # Clean up the temp file
                os.remove(temp_file_path)
                return render(request, 'result.html', {
                    'error': 'Could not extract any fashion keywords from the image. Please try a different image.'
                })
                
            print(f"Found {len(keywords)} keywords: {', '.join(keywords)}")
            
            # Fetch all videos
            all_videos = []
            
            # Fetch videos from all hard-coded accounts
            for username in FASHION_ACCOUNTS:
                try:
                    # Get reels for this username
                    print(f"Fetching videos for {username}")
                    user_videos = get_instagram_reels_by_username(username)
                    print(f"Got {len(user_videos)} videos from {username}")
                    
                    # Add username to each video for display purposes
                    for video in user_videos:
                        video['username'] = username
                    
                    all_videos.extend(user_videos)
                except Exception as e:
                    # If one account fails, continue with others
                    print(f"Error fetching videos from {username}: {e}")
                    continue
            
            print(f"Total videos fetched from all accounts: {len(all_videos)}")
            
            # Score videos based on keyword matches
            scored_videos = []
            for video in all_videos:
                video_hashtags = [tag.lower() for tag in video.get('hashtags', [])]
                
                # Count keyword matches
                match_count = 0
                matching_keywords = set()
                
                for keyword in keywords:
                    for hashtag in video_hashtags:
                        if keyword in hashtag:
                            match_count += 1
                            matching_keywords.add(keyword)
                            break
                
                # Only include videos with at least one match
                if match_count > 0:
                    # Add match info to the video
                    video['match_count'] = match_count
                    video['matching_keywords'] = list(matching_keywords)
                    scored_videos.append(video)
            
            # Sort by match count (highest first)
            sorted_videos = sorted(scored_videos, key=lambda x: x['match_count'], reverse=True)
            
            # Extract just the video URLs for backward compatibility
            video_urls = [video['video_url'] for video in sorted_videos]
            
            # The "hashtag" context variable will be used as a title
            combined_keywords = ", ".join(keywords[:5])  # Limit to first 5 for display
            if len(keywords) > 5:
                combined_keywords += "..."
            
            # Clean up the temp file
            os.remove(temp_file_path)
                
            return render(request, 'result.html', {
                'videos': sorted_videos,
                'video_urls': video_urls,
                'hashtag': combined_keywords,
                'count': len(sorted_videos),
                'accounts_searched': FASHION_ACCOUNTS,
                'is_image_search': True,
                'keywords': keywords,
                'uploaded_image': uploaded_image
            })
            
        except Exception as e:
            import traceback
            print(f"Error in image search: {str(e)}")
            print(traceback.format_exc())
            
            # Clean up temp file if it exists
            try:
                if 'temp_file_path' in locals():
                    os.remove(temp_file_path)
            except:
                pass
                
            return render(request, 'result.html', {'error': f'Error processing image: {str(e)}'})
            
    return redirect('search_video')

def analyze_image_with_gemini(image_input):
    """
    Analyze an image using Google's Gemini API to extract fashion-related keywords.
    
    Args:
        image_input: The uploaded image file or file path
    
    Returns:
        list: Fashion-related keywords extracted from the image
    """
    
    # Configure API key
    client = genai.Client(api_key="AIzaSyDy1bzPfSkaPih1dL5AtcSXxbjxJhc5ai8")
    
    try:
        # Now we're only handling file paths since we save the file first
        if not isinstance(image_input, str):
            raise ValueError("image_input must be a file path string")
            
        # Prepare the prompt
        prompt = """
        Analyze this fashion image and extract relevant keywords that describe:
        1. The type of clothing/outfit (e.g., dress, jeans, suit)
        2. Colors and patterns (e.g., red, floral, striped)
        3. Style categories (e.g., casual, formal, streetwear)
        4. Fashion elements or accessories (e.g., necklace, hat, boots)
        
        Return only fashion-specific keywords as a comma-separated list without explanations.
        Each keyword should be a single word or short phrase that could work as a hashtag.
        """
        
        # Use the built-in file upload with file path
        my_file = client.files.upload(file=image_input)

        # Generate content with the image and prompt
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[my_file, prompt],
        )
        
        # Extract and process keywords
        keywords_text = response.text.strip()
        keywords = [kw.strip().lower() for kw in keywords_text.split(',')]
        
        # Remove any '#' symbols if present and filter out very short keywords
        keywords = [kw.strip('#') for kw in keywords if len(kw.strip()) > 2]
        
        print(f"Extracted keywords from image: {keywords}")
        return keywords
        
    except Exception as e:
        print(f"Error analyzing image with Gemini: {str(e)}")
        import traceback
        print(traceback.format_exc())
        # Return a list of generic fashion keywords as fallback
        return ["fashion", "style", "outfit"]

def analyze_image_only(request):
    """API endpoint to analyze image and return keywords without searching videos"""
    if request.method == 'POST' and request.FILES.get('image'):
        try:
            image_file = request.FILES['image']
            
            # Create temp directory if it doesn't exist
            import os, uuid
            temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'temp_uploads')
            os.makedirs(temp_dir, exist_ok=True)
            
            # Generate a unique filename
            file_extension = os.path.splitext(image_file.name)[1].lower()
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            temp_file_path = os.path.join(temp_dir, unique_filename)
            
            # Save the uploaded file to disk
            with open(temp_file_path, 'wb+') as destination:
                for chunk in image_file.chunks():
                    destination.write(chunk)
            
            # Now pass the file path to the Gemini analysis function
            try:
                keywords = analyze_image_with_gemini(temp_file_path)
                # Clean up the temp file
                os.remove(temp_file_path)
                return JsonResponse({'keywords': keywords})
            except Exception as e:
                # Clean up the temp file in case of error
                os.remove(temp_file_path)
                raise e
                
        except Exception as e:
            import traceback
            print(f"Error in analyze_image_only: {str(e)}")
            print(traceback.format_exc())
            return JsonResponse({'error': str(e)}, status=400)
            
    return JsonResponse({'error': 'Invalid request'}, status=400)

def women_fashion_reels(request):
    """
    View function to display women's fashion reels filtered by women-related hashtags
    """
    try:
        all_videos = []
        women_fashion_tags = [
            'women']
        
        # Fetch videos from all fashion accounts
        for username in WOMEN_FASHION_ACCOUNTS:
            try:
                # Get reels for this username
                user_videos = get_instagram_reels_by_username(username)
                print(len(user_videos))
                # Filter videos containing women's fashion related hashtags
                for video in user_videos:
                    # video_hashtags = [tag.lower() for tag in video.get('hashtags', [])]
                    # if any(tag in video_hashtags for tag in women_fashion_tags):
                    #     video['matching_tags'] = [
                    #         tag for tag in video_hashtags
                    #         if tag in women_fashion_tags
                    #     ]
                    #     video['username'] = username
                    all_videos.append(video)
                
            except Exception as e:
                print(f"Error fetching videos from {username}: {e}")
                continue
        print(len(all_videos))
        # Sort videos by engagement (likes + views)
        # sorted_videos = sorted(
        #     all_videos,
        #     key=lambda x: x.get('like_count', 0) + x.get('view_count', 0),
        #     reverse=True
        # )

        # Extract video URLs for compatibility
        # video_urls = [video['video_url'] for video in sorted_videos]
        # print(video_urls)
        return render(request, 'womens.html', {
            'videos': all_videos,
            'video_urls': all_videos,
            'count': len(all_videos)
        })
        
    except Exception as e:
        import traceback
        print(f"Error in women_fashion_reels: {str(e)}")
        print(traceback.format_exc())
        return render(request, 'result.html', {
            'error': f'Error fetching women\'s fashion videos: {str(e)}'
        })

def men_fashion_reels(request):
    """
    View function to display men's fashion reels
    """
    try:
        all_videos = []
        men_fashion_tags = [
            'men', 'menswear', 'mensfashion', 'mensstyle', 'menstyle'
        ]
        
        # Fetch videos from men's fashion accounts
        for username in MEN_FASHION_ACCOUNTS:
            try:
                # Get reels for this username
                user_videos = get_instagram_reels_by_username(username)
                print(f"Got {len(user_videos)} videos from {username}")
                
                # Add username and other metadata
                for video in user_videos:
                    video['username'] = username
                    all_videos.append(video)
                
            except Exception as e:
                print(f"Error fetching videos from {username}: {e}")
                continue
        
        print(f"Total men's fashion videos: {len(all_videos)}")
        
        # Sort videos by engagement (likes + views) - optional
        sorted_videos = sorted(
            all_videos,
            key=lambda x: (x.get('like_count', 0) + x.get('view_count', 0)),
            reverse=True
        )
        
        return render(request, 'mens.html', {
            'videos': sorted_videos,
            'video_urls': sorted_videos,
            'count': len(sorted_videos)
        })
        
    except Exception as e:
        import traceback
        print(f"Error in men_fashion_reels: {str(e)}")
        print(traceback.format_exc())
        return render(request, 'result.html', {
            'error': f'Error fetching men\'s fashion videos: {str(e)}'
        })