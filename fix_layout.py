import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Extract tab-diagrama and the rogue </main> and <script>
regex_diagrama = r"(<!-- Tab 6: Diagrama Visual de Correlativas -->\s*<div class=\"tab-pane\" id=\"tab-diagrama\">.*?</div>\s*</main>\s*<script>.*?</script>\s*)"
match = re.search(regex_diagrama, content, flags=re.DOTALL)
if not match:
    print("Could not find tab-diagrama block")
    exit(1)

diagrama_block = match.group(1)
content = content.replace(diagrama_block, "")

# 2. Fix the Horario tab wrapping
content = content.replace(
    "<!-- Sección: Horario Semanal de Cursada (Calendario de Cursada) -->",
    "<div class=\"tab-pane\" id=\"tab-horario\">\n<!-- Sección: Horario Semanal de Cursada (Calendario de Cursada) -->"
)

# Replace the end of Horario section to close the tab
end_horario = """</div>
</section>
<!-- Contenedor Grid Principal -->"""
content = content.replace(end_horario, """</div>
</section>
</div>
<!-- Contenedor Grid Principal -->""")

# 3. Re-insert the diagrama block and main tag at the very end of the tabs, before modals
# We'll insert it right before <!-- Modal para Agregar Parcial -->
# But without the rogue </main>, we'll place </main> correctly
clean_diagrama = re.sub(r"</main>\s*", "", diagrama_block) # remove main

insertion_point = "<!-- Modal para Agregar Parcial -->"
content = content.replace(insertion_point, f"{clean_diagrama}\n</main>\n{insertion_point}")

# 4. Add z-index to main-nav
content = content.replace(
    ".main-nav {\n            background: var(--glass-bg);",
    ".main-nav {\n            position: relative;\n            z-index: 9999;\n            background: var(--glass-bg);"
)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Layout fixed!")
