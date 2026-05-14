import os

# --- KONFIGURACIJA ---
# Ovdje smo napravili listu svih ključnih fajlova za oba dijela aplikacije
# Ako se tvoji folderi zovu drugačije, samo ovdje promijeni ime (npr. umjesto 'frontend' stavi 'client')

files_to_combine = [
    # --- BACKEND FAJLOVI ---
    'main.py', 
    'models.py', 
    'schemas.py', 
    'database.py', 
    'security.py',
    
    # --- FRONTEND FAJLOVI ---
    # Koristimo ../ da izađemo iz backenda i uđemo u frontend
    '../frontend/src/App.jsx', 
    '../frontend/src/App.css',
    '../frontend/src/main.jsx',
    '../frontend/index.html'
]

output_file = 'allcodes.txt'

def combine_everything():
    print("="*60)
    print("🚀 SARA'S MASTER CODE COMBINER - ZAPOČINJEM RAD...")
    print("="*60)
    
    count = 0
    with open(output_file, 'w', encoding='utf-8') as outfile:
        # Prvo pišemo mali uvod u fajl
        outfile.write(f"PROJEKAT: GÖREV YÖNETİCİSİ (Full-Stack Code Capture)\n")
        outfile.write(f"DATUM SPAJANJA: {os.popen('date').read()}\n")
        outfile.write(f"{'#'*60}\n\n")

        for fname in files_to_combine:
            # Provjeravamo da li fajl uopšte postoji na toj adresi
            if os.path.exists(fname):
                print(f"🔍 Pronašao sam: {fname} (Dodajem...)")
                
                # Dodajemo naslovnu traku za svaki fajl u txt dokumentu
                outfile.write(f"\n\n{'/'*80}\n")
                outfile.write(f"/// FAJL: {fname}\n")
                outfile.write(f"{'/'*80}\n\n")
                
                # Čitamo sadržaj fajla i upisujemo ga u master fajl
                try:
                    with open(fname, 'r', encoding='utf-8') as infile:
                        outfile.write(infile.read())
                    count += 1
                except Exception as e:
                    outfile.write(f"\n[GREŠKA PRI ČITANJU FAJLA]: {str(e)}\n")
            else:
                # Ako Python ne može naći fajl, ispisat će nam upozorenje u terminalu
                print(f"⚠️ UPOZORENJE: Ne mogu naći {fname}. Provjeri putanju!")

    print("\n" + "="*60)
    print(f"✅ GOTOVO! Uspješno sam spojio {count} fajlova u '{output_file}'.")
    print("="*60)

if __name__ == "__main__":
    combine_everything()