import re
import os
import json
import sys

# --- Constants for Unicode Ranges ---
TANGUT_CHAR_REGEX = r'[\U00017000-\U000187FF]+'
CHINESE_CHAR_REGEX = r'[\u4e00-\u9fff]+' # Common Chinese characters

def load_json_data(file_path):
    """Loads JSON data from a specified file path."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: JSON file '{file_path}' not found. Please ensure it's in the same directory.")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{file_path}'. Please check file format.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while loading data from '{file_path}': {e}")
        return None

def load_tangut_data(lifanwen_file_path, compound_file_path):
    """
    Loads Tangut vocabulary data from two JSON files and builds translation dictionaries
    for English, Tangut, and Chinese, including compound word lookups.
    """
    # {Tangut_char/compound_string: {'phonetics': '...', 'meanings': [...], 'chinese_char': '...'}}
    tangut_phrases_to_meanings = {}

    # {english_word_lower: [{'char': '𘞗', 'phonetics': 'sjwɨ1', 'original_meaning': 'seed'}], ...}
    english_to_tangut = {}

    # {Tangut_char/compound_string: 'Chinese_char', ...} (for all direct Tangut->Chinese mappings)
    tangut_to_chinese = {}

    # {Chinese_char: [Tangut_char1, Tangut_char2], ...} (for all Chinese->Tangut mappings)
    chinese_to_tangut = {}

    # For tracking warnings
    total_li_fanwen_entries = 0
    total_compound_entries = 0
    total_entries_with_missing_phonetics = 0

    # Helper function to add mappings to english_to_tangut
    def add_to_english_map(key_phrase, tangut_char_display, phonetics_info, original_meaning_for_context):
        if not key_phrase: return

        # Normalize the phrase: remove punctuation, lowercase
        normalized_key_phrase = re.sub(r'[^\w\s]', '', key_phrase).lower()
        if not normalized_key_phrase: return

        entry = {
            'char': tangut_char_display, # This can be a single char or a compound string
            'phonetics': phonetics_info,
            'original_meaning': original_meaning_for_context
        }

        # Add the full normalized phrase as a lookup key
        english_to_tangut.setdefault(normalized_key_phrase, []).append(entry)

        # Add individual words from the phrase as lookup keys
        words_in_phrase = normalized_key_phrase.split()
        for word in words_in_phrase:
            if word:
                english_to_tangut.setdefault(word, []).append(entry)

    # --- 1. Load LiFanwenTangutList.json ---
    li_fanwen_data = load_json_data(lifanwen_file_path)
    if li_fanwen_data:
        total_li_fanwen_entries = len(li_fanwen_data)
        for entry in li_fanwen_data:
            char = entry.get("Character", "").strip()
            meaning_phrase = entry.get("Meaning", "").strip()
            keyword_phrase = entry.get("Keyword", "").strip()
            phonetics = entry.get("Phonetics", "").strip()
            chinese_char = entry.get("Chinese Character", "").strip()

            if not char:
                continue

            phonetics_to_store = phonetics
            if not phonetics:
                total_entries_with_missing_phonetics += 1
                phonetics_to_store = "<?MISSING_PHONETICS?>"

            # Populate tangut_phrases_to_meanings (for single characters)
            if char:
                meanings_list = []
                if meaning_phrase and meaning_phrase != '?':
                    meanings_list.append(meaning_phrase)
                if keyword_phrase and keyword_phrase != '?':
                    if keyword_phrase not in meanings_list: # Avoid duplicate meanings
                        meanings_list.append(keyword_phrase)
                tangut_phrases_to_meanings[char] = {
                    'phonetics': phonetics_to_store,
                    'meanings': meanings_list
                }

                # Populate english_to_tangut from Li Fanwen meanings
                if meaning_phrase and meaning_phrase != '?':
                    add_to_english_map(meaning_phrase, char, phonetics_to_store, meaning_phrase)
                if keyword_phrase and keyword_phrase != '?':
                    add_to_english_map(keyword_phrase, char, phonetics_to_store, meaning_phrase if meaning_phrase else keyword_phrase)

                # Populate Chinese mappings (Tangut <-> Chinese, for single characters)
                if chinese_char:
                    tangut_to_chinese[char] = chinese_char
                    chinese_to_tangut.setdefault(chinese_char, []).append(char)

    # --- 2. Load TangutCompoundWordsProposed.json ---
    compound_data = load_json_data(compound_file_path)
    if compound_data:
        total_compound_entries = len(compound_data)
        for entry in compound_data:
            modern_concept = entry.get("Modern Concept", "").strip()
            proposed_tangut_word_raw = entry.get("Proposed Tangut Word", "").strip() # E.g., "𗠾𗴾 (tsụ2wej2)"
            literal_tangut_meaning = entry.get("Literal Tangut Meaning", "").strip()

            if not proposed_tangut_word_raw:
                continue

            # Extract actual Tangut character(s) and phonetics from the raw string
            match = re.match(rf"({TANGUT_CHAR_REGEX}+)(?: \(([^)]+)\))?", proposed_tangut_word_raw)
            if match:
                tangut_char_for_map = match.group(1).strip() # This could be one or multiple chars
                phonetics_for_map = match.group(2).strip() if match.group(2) else "<?COMPOUND_PHONETICS_N/A?>"
            else:
                tangut_char_for_map = proposed_tangut_word_raw # Fallback if format is unexpected
                phonetics_for_map = "<?COMPOUND_PHONETICS_N/A?>"

            # Parse Modern Concept for both English and Chinese parts
            english_part_from_concept = None
            chinese_part_from_concept = None

            if modern_concept:
                # Try to extract Chinese character(s) at the beginning of the string
                initial_chinese_match = re.match(rf"({CHINESE_CHAR_REGEX}+)\s*(?:\([^)]+\))?", modern_concept)
                if initial_chinese_match:
                    chinese_part_from_concept = initial_chinese_match.group(1).strip()

                # Try to extract content inside parentheses for English part
                paren_content_match = re.search(r'\(([^)]+)\)', modern_concept)
                if paren_content_match:
                    english_part_from_concept = paren_content_match.group(1).strip()
                else: # If no parentheses, use the whole modern_concept if it doesn't start with Chinese
                    if not initial_chinese_match: # Only take whole string if no Chinese prefix
                        english_part_from_concept = modern_concept.strip()
                    else: # If there was a Chinese prefix, take anything after it as English
                        remaining_part = modern_concept[len(initial_chinese_match.group(0)):].strip()
                        if remaining_part and not re.match(rf"^{CHINESE_CHAR_REGEX}", remaining_part):
                            english_part_from_concept = remaining_part

            # Populate tangut_phrases_to_meanings with compound data
            compound_meanings_list = []
            if literal_tangut_meaning and literal_tangut_meaning != '?':
                compound_meanings_list.append(literal_tangut_meaning)
            if english_part_from_concept and english_part_from_concept != '?':
                if english_part_from_concept not in compound_meanings_list:
                    compound_meanings_list.append(english_part_from_concept)

            # Add/update the compound entry
            tangut_phrases_to_meanings[tangut_char_for_map] = {
                'phonetics': phonetics_for_map,
                'meanings': compound_meanings_list
            }

            # Add to english_to_tangut
            if english_part_from_concept:
                add_to_english_map(english_part_from_concept, tangut_char_for_map, phonetics_for_map, literal_tangut_meaning)
            if literal_tangut_meaning and literal_tangut_meaning != '?':
                add_to_english_map(literal_tangut_meaning, tangut_char_for_map, phonetics_for_map, literal_tangut_meaning)

            # Add to chinese_to_tangut if a Chinese character was extracted
            if chinese_part_from_concept:
                # Store the mapping from the Chinese char to the compound Tangut word
                chinese_to_tangut.setdefault(chinese_part_from_concept, []).append(tangut_char_for_map)
                # Also add the reverse mapping for Tangut compound to Chinese
                tangut_to_chinese[tangut_char_for_map] = chinese_part_from_concept


    # --- Deduplicate results for english_to_tangut and chinese_to_tangut ---
    # For English -> Tangut
    for key in english_to_tangut:
        seen_entries_for_key = set()
        unique_entries_for_key = []
        for entry in english_to_tangut[key]:
            entry_tuple = tuple(sorted(entry.items()))
            if entry_tuple not in seen_entries_for_key:
                seen_entries_for_key.add(entry_tuple)
                unique_entries_for_key.append(entry)
        english_to_tangut[key] = unique_entries_for_key

    # For Chinese -> Tangut, ensure unique Tangut chars as a sorted list
    for key in chinese_to_tangut:
        chinese_to_tangut[key] = sorted(list(set(chinese_to_tangut[key])))

    print(f"\nSummary: Loaded {total_li_fanwen_entries} Li Fanwen entries and {total_compound_entries} Proposed/Compound entries.")
    if total_entries_with_missing_phonetics > 0:
        print(f"Note: {total_entries_with_missing_phonetics} Li Fanwen entries had missing phonetics.")

    # Return None for dictionaries if any essential data failed to load
    if li_fanwen_data is None or compound_data is None:
        return None, None, None, None

    return tangut_phrases_to_meanings, english_to_tangut, tangut_to_chinese, chinese_to_tangut

# The translation functions now take tangut_phrases_to_meanings as the primary source for Tangut->X lookups
def translate_tangut_to_english(tangut_text, tangut_phrases_to_meanings):
    """
    Translates a Tangut text (string of characters/compounds) to English,
    prioritizing longer compound word matches.
    """
    if not tangut_phrases_to_meanings:
        return "Translation service not available (data not loaded)."

    detailed_results = []
    combined_meanings_set = set()
    combined_phonetics_list = []

    # Pre-calculate max length of Tangut keys for efficient lookup
    max_key_length = max(len(k) for k in tangut_phrases_to_meanings.keys()) if tangut_phrases_to_meanings else 1

    idx = 0
    while idx < len(tangut_text):
        found_match = False
        # Try to find the longest possible match starting from current index
        # Iterate from max_key_length down to 1
        for length in range(min(max_key_length, len(tangut_text) - idx), 0, -1):
            segment = tangut_text[idx : idx + length]
            segment_data = tangut_phrases_to_meanings.get(segment)

            if segment_data:
                # Found a match (can be single char or compound)
                meanings = segment_data.get('meanings', [])
                phonetics = segment_data.get('phonetics', '<?PHONETICS_N/A?>')
                detailed_results.append(f"'{segment}' ({phonetics}): {', '.join(meanings) if meanings else 'No meaning found'}")
                combined_meanings_set.update(meanings)
                combined_phonetics_list.append(phonetics)
                idx += length # Advance index by the length of the matched segment
                found_match = True
                break # Move to the next segment after this match

        if not found_match:
            # No match found for any length, treat as unknown
            char = tangut_text[idx] # This is the character that couldn't be matched
            detailed_results.append(f"'{char}': UNKNOWN CHARACTER")
            combined_phonetics_list.append("<?>")
            idx += 1 # Advance by 1 character

    output = []
    output.append("--- Word-by-Word Translation (Tangut -> English) ---")
    output.extend(detailed_results)
    output.append("---------------------------------------------------\n")

    output.append("--- Combined Phrase Details ---")
    output.append(f"Combined Meanings: {', '.join(sorted(list(combined_meanings_set)))}")
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

    normalized_text = re.sub(r'[^\w\s]', '', english_text).lower()
    words = normalized_text.split()

    detailed_results = []
    combined_tangut_chars_list = []
    combined_phonetics_list = []

    for word in words:
        matches = e_to_t_dict.get(word)
        if matches:
            sorted_matches = sorted(matches, key=lambda x: (x['char'], x['phonetics']))

            option_strings = []
            for match_info in sorted_matches:
                option_strings.append(f"'{match_info['char']}' ({match_info['phonetics']}) [from: '{match_info['original_meaning']}']")

            detailed_results.append(f"'{word}': {'; '.join(option_strings)}")

            # For combined phrase, pick the first match for simplicity
            first_match = sorted_matches[0]
            combined_tangut_chars_list.append(first_match['char'])
            combined_phonetics_list.append(first_match['phonetics'])
        else:
            detailed_results.append(f"'{word}': UNKNOWN WORD")
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

def translate_tangut_to_chinese(tangut_text, t_to_c_dict):
    """
    Translates a Tangut text (string of characters/compounds) to Chinese,
    prioritizing longer compound word matches.
    """
    if not t_to_c_dict:
        return "Translation service not available (Chinese data not loaded)."

    detailed_results = []
    combined_chinese_chars = []

    # Use the same longest-match logic as Tangut->English
    # Max length of a Tangut phrase that has a Chinese mapping
    max_key_length = max(len(k) for k in t_to_c_dict.keys()) if t_to_c_dict else 1

    idx = 0
    while idx < len(tangut_text):
        found_match = False
        for length in range(min(max_key_length, len(tangut_text) - idx), 0, -1):
            segment = tangut_text[idx : idx + length]
            chinese_char = t_to_c_dict.get(segment)

            if chinese_char:
                detailed_results.append(f"'{segment}': '{chinese_char}'")
                combined_chinese_chars.append(chinese_char)
                idx += length
                found_match = True
                break

        if not found_match:
            char = tangut_text[idx]
            detailed_results.append(f"'{char}': UNKNOWN OR NO CHINESE EQUIVALENT")
            combined_chinese_chars.append("<?>")
            idx += 1

    output = []
    output.append("--- Word-by-Word Translation (Tangut -> Chinese) ---")
    output.extend(detailed_results)
    output.append("---------------------------------------------------\n")

    output.append("--- Combined Phrase Details ---")
    output.append(f"Combined Chinese Phrase: {''.join(combined_chinese_chars)}")
    output.append("-------------------------------\n")

    return "\n".join(output)

def translate_chinese_to_tangut(chinese_text, c_to_t_dict):
    """
    Translates a Chinese text (string of characters) to Tangut.
    Presents multiple Tangut options if available.
    """
    if not c_to_t_dict:
        return "Translation service not available (Chinese data not loaded)."

    detailed_results = []
    combined_tangut_chars = []

    # Iterate over each Chinese character in the input string
    for char in chinese_text:
        tangut_matches = c_to_t_dict.get(char)
        if tangut_matches:
            # Sort for consistent output
            sorted_tangut_matches = sorted(tangut_matches)
            
            # 1. Create the string of joined matches first. This avoids complex syntax inside the f-string.
            matches_str = '; '.join(f"'{t_char}'" for t_char in sorted_tangut_matches)
            
            # 2. Now, use the simple variable in the main f-string.
            detailed_results.append(f"'{char}': {matches_str}")
            
            # For combined phrase, pick the first match (alphabetically sorted)
            combined_tangut_chars.append(sorted_tangut_matches[0])
        else:
            detailed_results.append(f"'{char}': UNKNOWN OR NO TANGUT EQUIVALENT")
            combined_tangut_chars.append("<?>")

    output = []
    output.append("--- Word-by-Word Translation (Chinese -> Tangut) ---")
    output.extend(detailed_results)
    output.append("---------------------------------------------------\n")

    output.append("--- Combined Phrase Details ---")
    output.append(f"Combined Tangut Phrase: {''.join(combined_tangut_chars)}")
    output.append("-------------------------------\n")

    return "\n".join(output)

def clear_screen():
    """Clears the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    # Define your file paths (ensure these match your actual files)
    li_fanwen_file = 'LiFanwenTangutList.json'
    compound_words_file = 'TangutCompoundWordsProposed.json'

    print("Loading Tangut data...")
    tangut_phrases_to_meanings, english_to_tangut_dict, tangut_to_chinese_dict, chinese_to_tangut_dict = \
        load_tangut_data(li_fanwen_file, compound_words_file)

    if tangut_phrases_to_meanings is None: # Check if essential data loaded
        print("Failed to load data. Exiting.")
        return

    print("\nTangut Raw Translator")
    print("---------------------")
    print("This is a raw, word-by-word translator based on the provided vocabulary lists.")
    print("For Tangut to English/Chinese, it prioritizes matching longer known phrases/compounds.")
    print("It does NOT understand grammar or complex context, and provides theoretical translations only.")
    print("For English/Chinese to Tangut, it will list all possible matches for a given word/character.")
    print("---------------------\n")

    while True:
        print("Choose a translation direction:")
        print("1. Tangut -> English")
        print("2. English -> Tangut")
        print("3. Tangut -> Chinese")
        print("4. Chinese -> Tangut")
        print("5. Exit")
        print("6. Clear Screen Output")
        choice = input("Enter your choice (1/2/3/4/5/6): ").strip()
        print("-" * 60)

        if choice == '1':
            while True:
                text_to_translate = input("Enter Tangut characters (e.g., 𘞗𘟇𘞼 or 𗲠𘔺) (or '/exit' to go back): ").strip()
                if text_to_translate.lower() == '/exit':
                    break
                if not text_to_translate:
                    print("Please enter some Tangut characters.")
                    continue
                # Pass tangut_phrases_to_meanings for the new longest-match logic
                print(translate_tangut_to_english(text_to_translate, tangut_phrases_to_meanings))
                print("=" * 60)
        elif choice == '2':
            while True:
                text_to_translate = input("Enter English text (e.g., sky river) (or '/exit' to go back): ").strip()
                if text_to_translate.lower() == '/exit':
                    break
                if not text_to_translate:
                    print("Please enter some English text.")
                    continue
                print(translate_english_to_tangut(text_to_translate, english_to_tangut_dict))
                print("=" * 60)
        elif choice == '3':
            while True:
                text_to_translate = input("Enter Tangut characters (e.g., 𗥈𗡼 or 𗲠𘔺) (or '/exit' to go back): ").strip()
                if text_to_translate.lower() == '/exit':
                    break
                if not text_to_translate:
                    print("Please enter some Tangut characters.")
                    continue
                # Pass tangut_to_chinese_dict for the new longest-match logic for Chinese
                print(translate_tangut_to_chinese(text_to_translate, tangut_to_chinese_dict))
                print("=" * 60)
        elif choice == '4':
            while True:
                text_to_translate = input("Enter Chinese characters (e.g., 協助 or 氧) (or '/exit' to go back): ").strip()
                if text_to_translate.lower() == '/exit':
                    break
                if not text_to_translate:
                    print("Please enter some Chinese characters.")
                    continue
                print(translate_chinese_to_tangut(text_to_translate, chinese_to_tangut_dict))
                print("=" * 60)
        elif choice == '5':
            print("Exiting translator...")
            break
        elif choice == '6':
            clear_screen()
        else:
            print("Invalid choice. Please enter 1, 2, 3, 4, 5, or 6.")
        print("=" * 60) # Main menu separator


if __name__ == "__main__":
    main()
