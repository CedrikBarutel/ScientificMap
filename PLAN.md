# IDEA OF THE PROJECT
The goal of the project is to have a overview of the academic public in Vienna. Particularly, it will be used to send invitation for seminar or short meeting to people who have a specific interested in the theme of the meeting. 

# TASKS 
1) Be able to scrap the information about academic people in Vienna and nearby (for instance ISTA). The information should contain:
 - name
 - main research keyword
 - working place
 - mail
 - link to other academic people (even outside Vienna)
 
2) Create different map with the people and their link. Their should be different way to group people, for instance working place, or research keywords.

3) Create a list of main topic, and main questions, and ideas of seminar/meeting that would be relevant for some group of people

x) Other tasks can come


# Constraints

# CURRENT REVIEW NOTES ADDED 2026-07-09

The current implementation already supports collection, enrichment, graph building, seminar suggestions, and campaign CSV export for manual review. The main recent update is the addition of a `location` field, a curated Vienna biophysics/soft-matter seed dataset, and safer campaign export that ignores invalid or obfuscated email values.

Immediate next steps should be source-specific parsers for major Vienna institutions, a persistent opt-out table, a field-cluster column, and better semantic topic matching.
