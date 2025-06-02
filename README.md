# Tangut Raw Translator

A **crude but powerful** command-line translator that brings the lost language of the **Tangut Empire (Western Xia)** back to life — one character at a time.

> ✨ Built by a passionate digital archaeologist.  
> 🧠 Powered by structured vocabulary from [Tangut.info](http://tangut.info) by Alan Downer.  
> 🔥 Open-source, free, and born from love for forgotten languages.

---

## 📖 What Is This?

**Tangut Raw Translator** is a simple Python-based tool that allows users to translate **English ➝ Tangut** and **Tangut ➝ English** using a structured dataset of over **6,000 Tangut characters**.

It’s *not* a full grammar-aware translator — just a **raw word-by-word match engine** based on known meanings, keywords, and phonetics.

---

## 📦 Features

- Translate from **English to Tangut**:  
  Get all relevant Tangut characters for a given word (e.g., `peace`, `sky`, `river`).

- Translate from **Tangut to English**:  
  See meanings, phonetics, and lexical data for any Tangut character.

- **Powered by JSON**:  
  Uses a structured `.json` file extracted and compiled from **Tangut.info** entries.

- Free. Local. Lightweight.  
  Run it offline, hack it, learn from it.

---

## 📝 Example Usage
python tangut_translator.py 
Loading Tangut data...
Summary: Loaded 6000 entries. 4 entries had missing phonetics.

Tangut Raw Translator
---------------------
This is a raw, word-by-word translator based on the provided vocabulary list.
It does NOT understand grammar or context, and provides theoretical translations only.
For English to Tangut, it will list all possible matches for a given word.
---------------------

Choose a translation direction:
1. Tangut -> English
2. English -> Tangut
3. Exit
4. Clear Screen Output
Enter your choice (1/2/3/4): 2
Enter English text (e.g., sky river): sky river
--- Word-by-Word Translation (English -> Tangut) ---
'sky': '𗳄' (kjɨ̲r2) [from: 'sky']; '𗹦' (mǝ1) [from: 'sky, heaven']; '𗽞' (thjɨj1) [from: 'sky']; '𘀗' (tshjwu1) [from: 'sky, heaven']; '𘓱' (me̲2) [from: 'sky, day']; '𘕿' (ɣa2) [from: 'locative particle in (the sky, the heart); on, around']
'river': '𗊝' (dźja̲1) [from: 'cross (a river)']; '𗊧' (tśhjwã1) [from: 'river']; '𗋽' (zjɨ̲r2) [from: 'water; river']; '𗌜' (njo̲r1) [from: 'water, river']; '𗡴' (śjwa1) [from: 'river']; '𗲌' (mja1) [from: 'river']; '𘖂' (ŋewr2) [from: 'river deer']
---------------------------------------------------

--- Combined Phrase Details ---
Combined Tangut Phrase: 𗳄𗊝
Combined Pronunciation: kjɨ̲r2 dźja̲1
-------------------------------

============================================================
Choose a translation direction:
1. Tangut -> English
2. English -> Tangut
3. Exit
4. Clear Screen Output
Enter your choice (1/2/3/4): 3
Exiting translator...


---
🙏 Credits & Data Source
This project uses compiled vocabulary entries and phonetic reconstructions based on the research and resources from:

Alan Downer – Tangut.info, especially the Tangut Vocabulary Data

Li Fanwen Dictionary for the reference numbering (LFW codes)

Xi Xia scholars and linguists who worked to preserve and decode Tangut script

If you use this project for further study or tools, please credit Alan Downer and Tangut.info.

📚 Why This Exists
The Tangut script was once the voice of a mighty empire. It fell into silence for centuries — until now.

This project was created by someone who refused to let Tangut remain forgotten. The goal?
✨ To revive, learn, and teach Tangut to the world.

📜 License
This project is open-source and free to use under the MIT License.
Knowledge is meant to be shared.

🌌 Final Note
If you read this far:
𗵻𗒐 (śja2 ɣiwej1) — Welcome.
𘚜𗅋𘒛 (lhjwịj1 mji1 mjịj2) — Tangut not forgotten.
