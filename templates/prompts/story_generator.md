You are creating a new running mission for a fitness game called "{{ game_name }}".

Main character:
{{ character }}

Story background:
{{ background }}

The player’s goal is to complete a mission by covering a total of
{% if mode == "distance" %}
{{ target_value }} kilometers.
{% else %}
running for {{ target_value }} minutes.
{% endif %}

Generate an immersive mission description that includes:
- A narrative setup (why they’re running)
- Objectives (what must be done or escaped)
- Motivation and emotional tension
- A clear success/failure condition

