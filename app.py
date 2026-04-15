# import os
# # Prevent OpenMP conflicting library error that could silently crash PyTorch/ONNX
# os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import streamlit as st
from PIL import Image
import io

# Set the page configuration for the web app
st.set_page_config(page_title="Background Remover App", page_icon="✂️", layout="wide")

# --- SIDEBAR ---
# Creating a sidebar for additional information about the project
st.sidebar.title("About the Developer")
st.sidebar.info(
    "Hello! I'm a student working on my python project. "
    "This Background Remover application demonstrates the integration of "
    "computer vision models (rembg) with a web frontend using Streamlit."
)

st.sidebar.title("How it Works")
st.sidebar.info(
    "1. Upload an image (JPG, JPEG, or PNG).\n"
    "2. The app uses an AI model to detect the main subject of the image.\n"
    "3. It automatically removes the background while preserving the subject.\n"
    "4. You can then download the final image with a transparent background as a PNG file!"
)

# --- MAIN PAGE ---
st.title("✂️ Professional Background Remover")
st.write("Upload an image below to magically remove its background using AI!")

# File uploader widget that accepts common image formats
uploaded_file = st.file_uploader("Choose an image...", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    # Open the uploaded image using Pillow (PIL)
    original_image = Image.open(uploaded_file)
    
    # Create two columns to display the before and after images side-by-side
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Original Image")
        # Display the original image
        st.image(original_image, use_container_width=True) # use_container_width used to avoid deprecation warnings
        
    with col2:
        st.subheader("Processed Image")
        # Show a spinner while the model is processing the image
        with st.spinner("Loading AI model & Removing background (First run downloads 170MB model!)..."):
            try:
                # Use rembg to remove the background (Import deferred here to stop UI freezing on launch!)
                from rembg import remove
                processed_image = remove(original_image)
                
                # Display the processed image with transparent background
                st.image(processed_image, use_container_width=True)
                
                # Convert the processed PIL Image to bytes for downloading
                # We save it as PNG to preserve the transparency
                img_byte_arr = io.BytesIO()
                processed_image.save(img_byte_arr, format='PNG')
                img_bytes = img_byte_arr.getvalue()
                
                # Add a download button for the user to save the result
                st.download_button(
                    label="Download Result (PNG)",
                    data=img_bytes,
                    file_name="background_removed.png",
                    mime="image/png"
                )
            except Exception as e:
                # In case something goes wrong, display an error message
                st.error(f"An error occurred during processing: {e}")

else:
    # Helpful message when no file is uploaded yet
    st.info("Please upload an image file to get started.")
