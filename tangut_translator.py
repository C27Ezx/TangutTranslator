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
        # Don't print an error if a file is explicitly designed to be optional (e.g., compound if not created yet)
        # For our case, both are expected, so an error is appropriate.
        print(f"Error: JSON file '{file_path}' not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{file_path}'. Please check its format.")
        return None
    except Exception as e:
        print(f"Error loading JSON file '{file_path}': {e}")
        return None

def load_tangut_data(lifanwen_file_path, compound_file_path):
    """
    Loads Tangut vocabulary data from two JSON files and builds translation dictionaries
    for English, Tangut, and Chinese.
    """
    tangut_char_data = {} # {Tangut_char: {'phonetics': 'sjwɨ1', 'meanings': ['seed', 'seed']}}
    english_to_tangut = {} # {english_word_lower: [{'char': '𘞗', 'phonetics': 'sjwɨ1', 'original_meaning': 'seed'}], ...}
    tangut_to_chinese = {} # {Tangut_char: 'Chinese_char', ...}
    chinese_to_tangut = {} # {Chinese_char: [Tangut_char1, Tangut_char2], ...}

    chars_with_missing_phonetics_warned = set()
    total_entries_with_missing_phonetics = 0
    total_li_fanwen_entries = 0
    total_compound_entries = 0

    # Helper function to add mappings to english_to_tangut
    def add_to_english_map(key_phrase, tangut_char, phonetics_info, original_meaning_for_context):
        if not key_phrase: return

        normalized_key_phrase = re.sub(r'[^\w\s]', '', key_phrase).lower()
        if not normalized_key_phrase: return

        # Add the full phrase
        entry = {'char': tangut_char, 'phonetics': phonetics_info, 'original_meaning': original_meaning_for_context}
        english_to_tangut.setdefault(normalized_key_phrase, []).append(entry)

        # Add individual words
        for word in normalized_key_phrase.split():
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
                continue # Skip entry if no character defined

            phonetics_to_store = phonetics
            if not phonetics:
                total_entries_with_missing_phonetics += 1
                phonetics_to_store = "<?MISSING_PHONETICS?>"
                # Don't print warnings for every char with missing phonetics, as it can spam
                # if char not in chars_with_missing_phonetics_warned:
                #    print(f"Warning: Li Fanwen char '{char}' has missing 'Phonetics'.")
                #    chars_with_missing_phonetics_warned.add(char)


            # Populate tangut_char_data (for Tangut -> English)
            if char not in tangut_char_data:
                tangut_char_data[char] = {'phonetics': phonetics_to_store, 'meanings': []}
            elif tangut_char_data[char]['phonetics'] == "<?MISSING_PHONETICS?>" and phonetics_to_store != "<?MISSING_PHONETICS?>":
                tangut_char_data[char]['phonetics'] = phonetics_to_store # Update if we found a phonetic

            if meaning_phrase and meaning_phrase != '?':
                if meaning_phrase not in tangut_char_data[char]['meanings']:
                    tangut_char_data[char]['meanings'].append(meaning_phrase)
                add_to_english_map(meaning_phrase, char, phonetics_to_store, meaning_phrase)
            if keyword_phrase and keyword_phrase != '?':
                if keyword_phrase not in tangut_char_data[char]['meanings']:
                    tangut_char_data[char]['meanings'].append(keyword_phrase)
                add_to_english_map(keyword_phrase, char, phonetics_to_store, meaning_phrase if meaning_phrase else keyword_phrase)

            # Populate Chinese mappings
            if chinese_char and char:
                tangut_to_chinese[char] = chinese_char
                chinese_to_tangut.setdefault(chinese_char, []).append(char)

    # --- 2. Load TangutCompoundWordsProposed.json ---
    compound_data = load_json_data(compound_file_path)
    if compound_data:
        total_compound_entries = len(compound_data)
        for entry in compound_data:
            modern_concept = entry.get("Modern Concept", "").strip()
            proposed_tangut_word_raw = entry.get("Proposed Tangut Word", "").strip() # Raw string like "𗠾 (tsụ2)"
            literal_tangut_meaning = entry.get("Literal Tangut Meaning", "").strip()

            if not proposed_tangut_word_raw:
                continue # Skip if no proposed word

            # Extract actual Tangut character(s) and phonetics from the raw string
            match = re.match(rf"({TANGUT_CHAR_REGEX})(?: \(([^)]+)\))?", proposed_tangut_word_raw)
            if match:
                tangut_char_for_map = match.group(1).strip()
                phonetics_for_map = match.group(2).strip() if match.group(2) else "<?N/A_COMPOUND_PHONETICS?>"
            else:
                tangut_char_for_map = proposed_tangut_word_raw # Fallback if no specific format
                phonetics_for_map = "<?N/A_COMPOUND_PHONETICS?>"


            # For compound words, we primarily augment the English -> Tangut map.
            # They don't typically go into `tangut_char_data` which is for single-character lookups.
            # The 'original_meaning' for context in these entries is 'literal_tangut_meaning'.

            if modern_concept:
                # 'Modern Concept' can be "English (Chinese)". Extract English part.
                eng_part_match = re.match(r"([^()]+)(?: \([^)]+\))?", modern_concept)
                english_part = eng_part_match.group(1).strip() if eng_part_match else modern_concept
                add_to_english_map(english_part, tangut_char_for_map, phonetics_for_map, literal_tangut_meaning)

            if literal_tangut_meaning and literal_tangut_meaning != '?':
                add_to_english_map(literal_tangut_meaning, tangut_char_for_map, phonetics_for_map, literal_tangut_meaning)


    # --- Deduplicate results for english_to_tangut and chinese_to_tangut ---
    for key in english_to_tangut:
        seen_entries_for_key = set()
        unique_entries_for_key = []
        for entry in english_to_tangut[key]:
            # Convert dict to a tuple of sorted items for hashability
            entry_tuple = tuple(sorted(entry.items()))
            if entry_tuple not in seen_entries_for_key:
                seen_entries_for_key.add(entry_tuple)
                unique_entries_for_key.append(entry)
        english_to_tangut[key] = unique_entries_for_key

    # For chinese_to_tangut, we just want unique Tangut chars as a list
    for key in chinese_to_tangut:
        chinese_to_tangut[key] = sorted(list(set(chinese_to_tangut[key])))

    print(f"\nSummary: Loaded {total_li_fanwen_entries} Li Fanwen entries and {total_compound_entries} Proposed/Compound entries.")
    if total_entries_with_missing_phonetics > 0:
        print(f"Note: {total_entries_with_missing_phonetics} Li Fanwen entries had missing phonetics.")

    # Return None for dictionaries if either initial load failed
    if li_fanwen_data is None or compound_data is None:
        return None, None, None, None

    return tangut_char_data, english_to_tangut, tangut_to_chinese, chinese_to_tangut

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
            phonetics = char_data['phonetics']
            detailed_results.append(f"'{char}' ({phonetics}): {', '.join(meanings) if meanings else 'No meaning found'}")
            combined_meanings_set.update(meanings)
            combined_phonetics_list.append(phonetics)
        else:
            detailed_results.append(f"'{char}': UNKNOWN CHARACTER")
            combined_phonetics_list.append("<?>")

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
    Translates a Tangut text (string of characters) to Chinese.
    """
    if not t_to_c_dict:
        return "Translation service not available (Chinese data not loaded)."

    detailed_results = []
    combined_chinese_chars = []

    for char in tangut_text:
        chinese_char = t_to_c_dict.get(char)
        if chinese_char:
            detailed_results.append(f"'{char}': '{chinese_char}'")
            combined_chinese_chars.append(chinese_char)
        else:
            detailed_results.append(f"'{char}': UNKNOWN OR NO CHINESE EQUIVALENT")
            combined_chinese_chars.append("<?>")

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
            detailed_results.append(f"'{char}': {'; '.join(f'\'{t_char}\'' for t_char in sorted_tangut_matches)}")
            # For combined phrase, pick the first match
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
    tangut_char_data_dict, english_to_tangut_dict, tangut_to_chinese_dict, chinese_to_tangut_dict = \
        load_tangut_data(li_fanwen_file, compound_words_file)

    if tangut_char_data_dict is None:
        print("Failed to load data. Exiting.")
        return

    print("\nTangut Raw Translator")
    print("---------------------")
    print("This is a raw, word-by-word translator based on the provided vocabulary lists.")
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
                text_to_translate = input("Enter Tangut characters (e.g., 𘞗𘟇𘞼) (or '/menu' to go back): ").strip()
                if text_to_translate.lower() == '/menu': # Changed to /menu
                    break
                if not text_to_translate:
                    print("Please enter some Tangut characters.")
                    continue
                print(translate_tangut_to_english(text_to_translate, tangut_char_data_dict))
                print("=" * 60)
        elif choice == '2':
            while True:
                text_to_translate = input("Enter English text (e.g., sky river) (or '/menu' to go back): ").strip()
                if text_to_translate.lower() == '/menu': # Changed to /menu
                    break
                if not text_to_translate:
                    print("Please enter some English text.")
                    continue
                print(translate_english_to_tangut(text_to_translate, english_to_tangut_dict))
                print("=" * 60)
        elif choice == '3':
            while True:
                text_to_translate = input("Enter Tangut characters (e.g., 𗥈𗡼) (or '/menu' to go back): ").strip()
                if text_to_translate.lower() == '/menu': # Changed to /menu
                    break
                if not text_to_translate:
                    print("Please enter some Tangut characters.")
                    continue
                print(translate_tangut_to_chinese(text_to_translate, tangut_to_chinese_dict))
                print("=" * 60)
        elif choice == '4':
            while True:
                text_to_translate = input("Enter Chinese characters (e.g., 協助) (or '/menu' to go back): ").strip()
                if text_to_translate.lower() == '/menu': # Changed to /menu
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
    # >>> IMPORTANT: REMOVE OR COMMENT OUT THIS BLOCK AFTER YOUR REAL JSON FILES ARE IN PLACE <<<
    # This block is for initial demonstration if you don't have the files yet.
    # If your actual files exist, this will overwrite them or cause the translator to load the small dummy data.
    if not os.path.exists('LiFanwenTangutList.json'):
        print("\n--- WARNING: Creating a dummy LiFanwenTangutList.json for demonstration. ---")
        print("--- Please ensure your actual file is named 'LiFanwenTangutList.json' and is in this directory. ---")
        print("--- If you have your real data, delete this warning block and the dummy creation code. ---\n")
        dummy_li_fanwen = [
            {"Character": "𘞗", "Li Fanwen Number": "1", "Meaning": "seed", "Keyword": "seed", "Phonetics": "sjwɨ1", "Part of Speech": "N", "Phonetic Class": "Dental-Affricate", "Unicode Hex Value": "18797", "Chinese Character": "籽"},
            {"Character": "𘟇", "Li Fanwen Number": "2", "Meaning": "filter", "Keyword": "filter", "Phonetics": "lo1", "Part of Speech": "N", "Phonetic Class": "Liquid", "Unicode Hex Value": "187C7", "Chinese Character": "滤"},
            {"Character": "𗠾", "Li Fanwen Number": "100", "Meaning": "cough", "Keyword": "cough", "Phonetics": "tsụ2", "Part of Speech": "V", "Phonetic Class": "Gutteral", "Unicode Hex Value": "1783E", "Chinese Character": "咳"},
            {"Character": "𘞼", "Li Fanwen Number": "3", "Meaning": "mother", "Keyword": "mother", "Phonetics": "sji2", "Part of Speech": "N", "Phonetic Class": "Dental-Affricate", "Unicode Hex Value": "187BC", "Chinese Character": "母"},
            {"Character": "𘘦", "Li Fanwen Number": "500", "Meaning": "particle", "Keyword": "particle", "Phonetics": "la1", "Part of Speech": "P", "Phonetic Class": "Liquid", "Unicode Hex Value": "18626", "Chinese Character": "啦"},
            {"Character": "𗴾", "Li Fanwen Number": "600", "Meaning": "store", "Keyword": "store", "Phonetics": "wej2", "Part of Speech": "V", "Phonetic Class": "Labial", "Unicode Hex Value": "17D3E", "Chinese Character": "蓄"},
            {"Character": "𗥈", "Li Fanwen Number": "123", "Meaning": "cooperation", "Keyword": "cooperation", "Phonetics": "siep2", "Part of Speech": "N", "Phonetic Class": "Gutteral", "Unicode Hex Value": "17D48", "Chinese Character": "協"},
            {"Character": "𗡼", "Li Fanwen Number": "124", "Meaning": "help", "Keyword": "help", "Phonetics": "tsiu2", "Part of Speech": "V", "Phonetic Class": "Gutteral", "Unicode Hex Value": "1787C", "Chinese Character": "助"},
            {"Character": "𗍅", "Li Fanwen Number": "125", "Meaning": "worker", "Keyword": "worker", "Phonetics": "kong1", "Part of Speech": "N", "Phonetic Class": "Gutteral", "Unicode Hex Value": "17345", "Chinese Character": "工"},
            {"Character": "𗽻", "Li Fanwen Number": "126", "Meaning": "tool", "Keyword": "tool", "Phonetics": "kiu2", "Part of Speech": "N", "Phonetic Class": "Gutteral", "Unicode Hex Value": "17F7B", "Chinese Character": "具"},
            {"Character": "𘒨", "Li Fanwen Number": "127", "Meaning": "set up", "Keyword": "set up", "Phonetics": "siet1", "Part of Speech": "V", "Phonetic Class": "Gutteral", "Unicode Hex Value": "18428", "Chinese Character": "設"},
            {"Character": "𗲺", "Li Fanwen Number": "128", "Meaning": "firm", "Keyword": "firm", "Phonetics": "deng2", "Part of Speech": "A", "Phonetic Class": "Dental", "Unicode Hex Value": "17CB8", "Chinese Character": "定"},
            {"Character": "𗱅", "Li Fanwen Number": "130", "Meaning": "down", "Keyword": "down", "Phonetics": "ha2", "Part of Speech": "P", "Phonetic Class": "Gutteral", "Unicode Hex Value": "17C45", "Chinese Character": "下"},
            {"Character": "𗋽", "Li Fanwen Number": "7", "Meaning": "water", "Keyword": "water", "Phonetics": "ljɨ1", "Part of Speech": "N", "Phonetic Class": "Liquid", "Unicode Hex Value": "17C45", "Chinese Character": "水"},
            {"Character": "𗡴", "Li Fanwen Number": "8", "Meaning": "river", "Keyword": "river", "Phonetics": "ngwia1", "Part of Speech": "N", "Phonetic Class": "Liquid", "Unicode Hex Value": "17854", "Chinese Character": "河"},
            {"Character": "𗱸", "Li Fanwen Number": "9", "Meaning": "stone", "Keyword": "stone", "Phonetics": "njo1", "Part of Speech": "N", "Phonetic Class": "Dental", "Unicode Hex Value": "17C78", "Chinese Character": "石"},
            {"Character": "𘄂", "Li Fanwen Number": "10", "Meaning": "clear", "Keyword": "clear", "Phonetics": "nja2", "Part of Speech": "A", "Phonetic Class": "Dental", "Unicode Hex Value": "18102", "Chinese Character": "清"},
            {"Character": "𗙏", "Li Fanwen Number": "11", "Meaning": "sound", "Keyword": "sound", "Phonetics": "tjɨ2", "Part of Speech": "N", "Phonetic Class": "Dental", "Unicode Hex Value": "1764F", "Chinese Character": "聲"},
        ]
        with open('LiFanwenTangutList.json', 'w', encoding='utf-8') as f:
            json.dump(dummy_li_fanwen, f, indent=2, ensure_ascii=False)

    if not os.path.exists('TangutCompoundWordsProposed.json'):
        print("\n--- WARNING: Creating a dummy TangutCompoundWordsProposed.json for demonstration. ---")
        print("--- Please ensure your actual file is named 'TangutCompoundWordsProposed.json' and is in this directory. ---")
        print("--- If you have your real data, delete this warning block and the dummy creation code. ---\n")
        dummy_compound = [
            {"Modern Concept": "New Compound Word (新复合词)", "Proposed Tangut Word": "𗠾𗴾 (tsụ2wej2)", "Literal Tangut Meaning": "Cough Store (example of compound)", "Reasoning/Explanation": "This is a new compound word."},
            {"Modern Concept": "Unknown Character (未知字符)", "Proposed Tangut Word": "𗘬", "Literal Tangut Meaning": "Unknown", "Reasoning/Explanation": "This character is not in Li Fanwen list."},
            {"Modern Concept": "Sea Stone", "Proposed Tangut Word": "𗗚𗱸", "Literal Tangut Meaning": "Sea Stone", "Reasoning/Explanation": "Compound word"},
            {"Modern Concept": "Green Stone", "Proposed Tangut Word": "𗘍𗱸", "Literal Tangut Meaning": "Green Stone", "Reasoning/Explanation": "Compound word"},
            {"Modern Concept": "Stone Clear", "Proposed Tangut Word": "𗱸𘄂", "Literal Tangut Meaning": "Stone Clear", "Reasoning/Explanation": "Compound word"},
            {"Modern Concept": "Stone Beat", "Proposed Tangut Word": "𗱸𘄩", "Literal Tangut Meaning": "Stone Beat", "Reasoning/Explanation": "Compound word"},
            {"Modern Concept": "Clear Stone", "Proposed Tangut Word": "𘄂𗱸", "Literal Tangut Meaning": "Clear Stone", "Reasoning/Explanation": "Compound word"},
            {"Modern Concept": "Honour Stone", "Proposed Tangut Word": "𘅧𗱸", "Literal Tangut Meaning": "Honour Stone", "Reasoning/Explanation": "Compound word"},
            {"Modern Concept": "Fire Stone", "Proposed Tangut Word": "𘓼𗱸", "Literal Tangut Meaning": "Fire Stone", "Reasoning/Explanation": "Compound word"},
            {"Modern Concept": "Mother Old Aged", "Proposed Tangut Word": "𘞼𘒺", "Literal Tangut Meaning": "Mother Old Aged", "Reasoning/Explanation": "Compound word"},
            {"Modern Concept": "Water Sprinkle", "Proposed Tangut Word": "𗋽𗃊", "Literal Tangut Meaning": "Water Sprinkle", "Reasoning/Explanation": "Compound word"},
            {"Modern Concept": "Water Move", "Proposed Tangut Word": "𗋽𗇾", "Literal Tangut Meaning": "Water Move", "Reasoning/Explanation": "Compound word"},
            {"Modern Concept": "Water Sound", "Proposed Tangut Word": "𗋽𗙏", "Literal Tangut Meaning": "Water Sound", "Reasoning/Explanation": "Compound word"},
            {"Modern Concept": "Water Moist", "Proposed Tangut Word": "𗋽𗱥", "Literal Tangut Meaning": "Water Moist", "Reasoning/Explanation": "Compound word"},
            {"Modern Concept": "Water Land", "Proposed Tangut Word": "𗋽𗼻", "Literal Tangut Meaning": "Water Land", "Reasoning/Explanation": "Compound word"},
            {"Modern Concept": "Sea Water", "Proposed Tangut Word": "𗗚𗋽", "Literal Tangut Meaning": "Sea Water", "Reasoning/Explanation": "Compound word"},
            {"Modern Concept": "Deep Water", "Proposed Tangut Word": "𘜩𗋽", "Literal Tangut Meaning": "Deep Water", "Reasoning/Explanation": "Compound word"},
        ]
        with open('TangutCompoundWordsProposed.json', 'w', encoding='utf-8') as f:
            json.dump(dummy_compound, f, indent=2, ensure_ascii=False)
            
    # Run the main translator application
    main()
