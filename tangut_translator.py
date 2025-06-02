import re
import os
import json

def load_tangut_data(filename="tangut_learning_data.txt"):
    """
    Loads Tangut vocabulary data from a JSON file and builds translation dictionaries.
    """
    # Stores comprehensive data for each Tangut character:
    # {Tangut_char: {'phonetics': 'sjwɨ1', 'meanings': ['seed', 'seed']}}
    tangut_char_data = {} 
    
    # Stores mappings from English words/phrases to Tangut characters, with context:
    # {english_word_lower: [{'char': '𘞗', 'phonetics': 'sjwɨ1', 'original_meaning': 'seed'}], ...}
    english_to_tangut = {} 
    
    # To track warnings about missing phonetics
    chars_with_missing_phonetics_warned = set()
    total_entries_with_missing_phonetics = 0

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f) # Load the entire JSON array from the file
            
            for entry in data: # Iterate through each dictionary (character entry) in the loaded JSON data
                # Use .get() with a default empty string to handle potentially missing keys gracefully
                char = entry.get("Character", "").strip()
                meaning_phrase = entry.get("Meaning", "").strip()
                keyword_phrase = entry.get("Keyword", "").strip()
                phonetics = entry.get("Phonetics", "").strip() # This is the field often empty

                # Fundamental validation: Character itself is essential for mapping
                if not char:
                    print(f"Warning: Skipping entry due to a missing 'Character' field. Entry: {entry}")
                    continue

                # Handle missing phonetics: use a placeholder and issue a warning
                phonetics_to_store = phonetics
                if not phonetics:
                    total_entries_with_missing_phonetics += 1
                    phonetics_to_store = "<?MISSING_PHONETICS?>"
                    if char not in chars_with_missing_phonetics_warned:
                        print(f"Warning: Character '{char}' has missing 'Phonetics'. Using placeholder '<?MISSING_PHONETICS?>'.")
                        chars_with_missing_phonetics_warned.add(char)
                
                # --- Populate tangut_char_data ---
                # Initialize or update entry for the character
                if char not in tangut_char_data:
                    tangut_char_data[char] = {'phonetics': phonetics_to_store, 'meanings': []}
                else:
                    # If an entry exists and its phonetics were previously missing, but we now found one, update.
                    # This handles cases where the same character might appear multiple times
                    # but only some entries have phonetics.
                    if tangut_char_data[char]['phonetics'] == "<?MISSING_PHONETICS?>" and phonetics_to_store != "<?MISSING_PHONETICS?>":
                         tangut_char_data[char]['phonetics'] = phonetics_to_store
                
                # Add unique meanings/keywords to the list for this char
                if meaning_phrase and meaning_phrase != '?' and meaning_phrase not in tangut_char_data[char]['meanings']:
                    tangut_char_data[char]['meanings'].append(meaning_phrase)
                if keyword_phrase and keyword_phrase != '?' and keyword_phrase not in tangut_char_data[char]['meanings']:
                    tangut_char_data[char]['meanings'].append(keyword_phrase)

                # --- Populate english_to_tangut ---
                phrases_to_process = [meaning_phrase, keyword_phrase]
                
                for phrase_source in phrases_to_process:
                    if phrase_source and phrase_source != '?':
                        # Normalize the phrase: remove punctuation, lowercase
                        normalized_phrase_key = re.sub(r'[^\w\s]', '', phrase_source).lower() 
                        
                        # Add the full normalized phrase as a lookup key
                        if normalized_phrase_key:
                            english_to_tangut.setdefault(normalized_phrase_key, []).append({
                                'char': char, 
                                'phonetics': phonetics_to_store, 
                                'original_meaning': meaning_phrase # Store the primary meaning for context
                            })
                        
                        # Add individual words from the phrase as lookup keys
                        words_in_phrase = normalized_phrase_key.split()
                        for word in words_in_phrase:
                            if word:
                                english_to_tangut.setdefault(word, []).append({
                                    'char': char, 
                                    'phonetics': phonetics_to_store, 
                                    'original_meaning': meaning_phrase
                                })

    except FileNotFoundError:
        print(f"Error: Data file '{filename}' not found. Please ensure it's in the same directory.")
        return None, None
    except json.JSONDecodeError as e:
        print(f"Error: Could not decode JSON from '{filename}'. Please check file format. Details: {e}")
        return None, None
    except Exception as e:
        print(f"An unexpected error occurred while loading data: {e}")
        return None, None

    # Final filtering for english_to_tangut to ensure uniqueness of mappings
    # This prevents listing the same (char, phonetics, original_meaning) multiple times for one English word
    for key in english_to_tangut:
        seen_entries_for_key = set()
        unique_entries_for_key = []
        for entry in english_to_tangut[key]:
            entry_tuple = (entry['char'], entry['phonetics'], entry['original_meaning']) # Create a tuple for set comparison
            if entry_tuple not in seen_entries_for_key:
                seen_entries_for_key.add(entry_tuple)
                unique_entries_for_key.append(entry)
        english_to_tangut[key] = unique_entries_for_key

    if total_entries_with_missing_phonetics > 0:
        print(f"\nSummary: Loaded {len(data)} entries. {total_entries_with_missing_phonetics} entries had missing phonetics.")
    else:
        print(f"\nSummary: Loaded {len(data)} entries. No missing phonetics warnings.")
    
    return tangut_char_data, english_to_tangut

def translate_tangut_to_english(tangut_text, t_data_dict):
    """
    Translates a Tangut text (string of characters) to English word-by-word,
    and provides combined phrase details.
    """
    if not t_data_dict:
        return "Translation service not available (data not loaded)."

    detailed_results = []
    combined_meanings_set = set()
    combined_phonetics_list = []

    for char in tangut_text:
        char_data = t_data_dict.get(char)
        if char_data:
            meanings = char_data['meanings']
            phonetics = char_data['phonetics'] # This will now contain "<?MISSING_PHONETICS?>" if empty in source
            detailed_results.append(f"'{char}' ({phonetics}): {', '.join(meanings) if meanings else 'No meaning found'}")
            combined_meanings_set.update(meanings)
            combined_phonetics_list.append(phonetics)
        else:
            detailed_results.append(f"'{char}': UNKNOWN CHARACTER")
            # For combined phrase, add a placeholder
            combined_phonetics_list.append("<?>") 

    output = []
    output.append("--- Word-by-Word Translation (Tangut -> English) ---")
    output.extend(detailed_results)
    output.append("---------------------------------------------------\n")
    
    output.append("--- Combined Phrase Details ---")
    output.append(f"Combined Meanings: {', '.join(sorted(list(combined_meanings_set)))}")
    # Handle cases where some phonetics might be missing due to UNKNOWN chars or empty source data
    output.append(f"Combined Pronunciation: {' '.join(combined_phonetics_list)}")
    output.append("-------------------------------\n")
    
    return "\n".join(output)

def translate_english_to_tangut(english_text, e_to_t_dict):
    """
    Translates an English text to Tangut word-by-word and provides combined phrases.
    Lists multiple Tangut options if available.
    """
    if not e_to_t_dict:
        return "Translation service not available (data not loaded)."

    # Normalize input text: lowercase and remove punctuation
    normalized_text = re.sub(r'[^\w\s]', '', english_text).lower()
    words = normalized_text.split()

    detailed_results = []
    combined_tangut_chars_list = []
    combined_phonetics_list = []

    for word in words:
        matches = e_to_t_dict.get(word)
        if matches:
            # Sort matches for consistent output (e.g., by character then phonetics)
            sorted_matches = sorted(matches, key=lambda x: (x['char'], x['phonetics']))
            
            option_strings = []
            for match_info in sorted_matches:
                # Use the phonetics stored in the dict, which could be the placeholder
                option_strings.append(f"'{match_info['char']}' ({match_info['phonetics']}) [from: '{match_info['original_meaning']}']")
            
            detailed_results.append(f"'{word}': {'; '.join(option_strings)}")
            
            # For combined phrase, pick the first match (e.g., the one that comes first alphabetically by char/phonetics)
            first_match = sorted_matches[0]
            combined_tangut_chars_list.append(first_match['char'])
            combined_phonetics_list.append(first_match['phonetics'])
        else:
            detailed_results.append(f"'{word}': UNKNOWN WORD")
            # If unknown, add a placeholder for combined phrase
            combined_tangut_chars_list.append("<?>") 
            combined_phonetics_list.append("<?ph?>")

    output = []
    output.append("--- Word-by-Word Translation (English -> Tangut) ---")
    output.extend(detailed_results)
    output.append("---------------------------------------------------\n")

    output.append("--- Combined Phrase Details ---")
    output.append(f"Combined Tangut Phrase: {''.join(combined_tangut_chars_list)}")
    output.append(f"Combined Pronunciation: {' '.join(combined_phonetics_list)}")
    output.append("-------------------------------\n")

    return "\n".join(output)

def clear_screen():
    """Clears the terminal screen."""
    # 'cls' for Windows, 'clear' for macOS/Linux
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    print("Loading Tangut data...")
    tangut_char_data_dict, english_to_tangut_dict = load_tangut_data()

    if tangut_char_data_dict is None:
        print("Failed to load data. Exiting.")
        return

    print("\nTangut Raw Translator")
    print("---------------------")
    print("This is a raw, word-by-word translator based on the provided vocabulary list.")
    print("It does NOT understand grammar or context, and provides theoretical translations only.")
    print("For English to Tangut, it will list all possible matches for a given word.")
    print("---------------------\n")

    while True:
        print("Choose a translation direction:")
        print("1. Tangut -> English")
        print("2. English -> Tangut")
        print("3. Exit")
        print("4. Clear Screen Output")
        choice = input("Enter your choice (1/2/3/4): ").strip()

        if choice == '1':
            text_to_translate = input("Enter Tangut characters (e.g., 𘞗𘟇𘞼): ").strip()
            print(translate_tangut_to_english(text_to_translate, tangut_char_data_dict))
        elif choice == '2':
            text_to_translate = input("Enter English text (e.g., sky river): ").strip()
            print(translate_english_to_tangut(text_to_translate, english_to_tangut_dict))
        elif choice == '3':
            print("Exiting translator...")
            break
        elif choice == '4':
            clear_screen()
        else:
            print("Invalid choice. Please enter 1, 2, 3, or 4.")
        print("=" * 60) # Use a longer separator for clarity


if __name__ == "__main__":
    main()
