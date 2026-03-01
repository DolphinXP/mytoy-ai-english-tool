
You are professional product manager and software engineer.
I want to you to make a pdf viewer app with the 读书笔记 functions.
You design and develop an app which has follwoing functions:

0. This project is heavily related to the parent project: AI-TTS, 
   lots of functions and implementation can inherent from parent.
1. Support PDF view, can open pdf file then display it.
2. User can select text in pdf file.
3. When user selecting text, a popup menu which contains Translation and AI Explain.
4. When user clicked translation on poup menu, it will translate the selected text like the 
  parent AI-TTS: correct text -> translate to chinese(mainly) -> make tts then play it.
5. These translated result should be displayed another panel like parent popup_window
6. The translation result panel also includes functions like parent popup_window like copy/edit/retranslate/explain/play tts and quick dictionary, except exit program
7. Like the parent AI-TTS, all these functions is based on api call and based on current context of selected text
8. After the translation of selected text, the selected text on pdf view should be highlighted that user can notice the next time read this document.
   all these result should also be recorded so when user can navigate to highlighted text to view the translation and the related results of previous operations.
   You also provide regenerate button to give user the chance to update the result.
9. The ai explain in popup provides ai explanation of selected text in the context, the implement is like the translation.
10. The programming language is python, and the conda environment is vibevoice.

use 2 agents to do work.