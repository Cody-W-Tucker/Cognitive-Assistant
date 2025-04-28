import re


def clean_text(text):
    # Convert text to lowercase
    text = text.lower()

    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text)

    # Remove punctuation (except apostrophes)
    text = re.sub(r"[^\w\s\']", "", text)

    return text


# Read the text file
with open("transcriptions/Tuesday at 9-49 AM.txt", "r") as file:
    original_text = file.read()

# Clean the text
cleaned_text = clean_text(original_text)

# Write the cleaned text to a new file
with open("transcriptions/cleaned_transcription.txt", "w") as file:
    file.write(cleaned_text)

print("Text cleaned and saved to 'cleaned_transcription.txt'.")
