# Input locali

L'app parte senza dati: creare un progetto dall'interfaccia e caricare il suo Excel.
I workbook caricati vengono salvati nell'archivio `runtime/`, escluso da Git.

Il file facoltativo `base.xlsx` serve solo per migrare una precedente installazione
locale: se l'archivio è vuoto, viene importato come primo progetto. Non è necessario
per avviare l'app e non viene incluso nel repository o nell'immagine Docker.
