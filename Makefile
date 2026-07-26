.PHONY: test verify lookup autodro reproduce paper

test:
	PYTHONPATH=. python3 -m unittest discover -s tests -v

verify:
	PYTHONPATH=. python3 verify_artifacts.py

lookup:
	PYTHONPATH=. python3 generate_lookup_benchmark.py

autodro:
	PYTHONPATH=. python3 generate_autodro_benchmark.py

reproduce:
	PYTHONPATH=. python3 build_all.py --benchmark-mode max

paper:
	cd paper && pdflatex -interaction=nonstopmode main.tex && bibtex main && pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex
