"""French to English for the short controlled vocabularies of Mérimée and Palissy.

Free text (history, protection notes, titles, captions) is not translated: pages link it to a translator.
A term missing here is shown in French.
"""

DENOMINATION = {
    "église": "church", "chapelle": "chapel", "abbaye": "abbey", "prieuré": "priory", "couvent": "convent",
    "cathédrale": "cathedral", "commanderie": "commandery", "cimetière": "cemetery", "site archéologique": "archaeological site",
    "collégiale": "collegiate church", "oratoire": "oratory", "presbytère": "presbytery", "château": "château",
    "croix de cimetière": "cemetery cross", "basilique": "basilica", "temple": "Protestant church", "maison": "house",
    "calvaire monumental": "monumental calvary", "immeuble": "building", "fortification d'agglomération": "town fortification",
    "croix monumentale": "monumental cross", "hôtel-Dieu": "hôtel-Dieu (hospital)", "ensemble fortifié": "fortified complex",
    "manoir": "manor", "hôtel": "town house", "tour": "tower", "hôpital": "hospital", "chapelle funéraire": "funerary chapel",
    "église dite chapelle": "church known as a chapel", "moulin": "mill", "maladrerie": "leper house",
    "établissement conventuel": "conventual house", "université": "university", "maison forte": "fortified house",
    "établissement de bienfaisance": "charitable institution", "château fort": "castle", "oradour": "oratory",
    "ensemble cathédral": "cathedral complex", "quartier canonial": "canons' quarter", "synagogue": "synagogue",
    "palais épiscopal": "bishop's palace", "hospice": "hospice", "baptistère": "baptistery", "archevêché": "archbishop's palace",
    "enclos": "enclosure", "fortification": "fortification", "édifice fortifié": "fortified building", "pilori": "pillory",
    "aumônerie": "almonry", "grange monastique": "monastic barn", "collège": "college", "halle": "market hall", "école": "school",
    "séminaire": "seminary", "fontaine de dévotion": "holy well", "prison": "prison", "ermitage": "hermitage", "caserne": "barracks",
    "pont": "bridge", "ensemble religieux": "religious complex", "théâtre": "theatre",
}

CRAFT = {
    "sculpture": "sculpture", "menuiserie": "joinery", "peinture": "painting", "orfèvrerie": "goldsmith's work",
    "taille de pierre": "stone carving", "fonderie de cloches": "bell founding", "fonderie de cloche": "bell founding",
    "vitrail": "stained glass", "tissu": "textiles", "facture d'orgue": "organ building", "facture d’orgue": "organ building",
    "facteur d'orgue": "organ building", "marbrerie": "marble work", "peinture murale": "wall painting",
    "peintures murales": "wall painting", "peinture monumentale": "monumental painting", "ferronnerie": "wrought iron",
    "fonderie": "metal casting", "dinanderie": "brassware", "bronze d'art": "art bronze", "bronze d’art": "art bronze",
    "menuiserie ébénisterie": "joinery and cabinetmaking", "menuiserie-ébénisterie": "joinery and cabinetmaking",
    "céramique": "ceramics", "poterie d'étain": "pewter", "verrerie": "glassware", "tapisserie sur métier": "loom tapestry",
    "ébénisterie": "cabinetmaking", "imprimerie": "printing", "horlogerie": "clockmaking", "ferblanterie": "tinware",
    "broderie": "embroidery", "estampe": "prints", "dessin": "drawing", "peausserie": "leather", "gypserie": "plasterwork",
    "maroquinerie": "fine leather", "émaillerie": "enamel", "mosaïque": "mosaic", "tabletterie": "small carved wares",
    "facture d'instruments de musique": "instrument making", "facture d'instrument de musique": "instrument making",
    "facture d'harmonium": "harmonium building", "facture d’harmonium": "harmonium building", "maçonnerie": "masonry",
    "reliure": "bookbinding", "armurerie": "arms and armour", "charpente": "carpentry", "charronnage": "wheelwright's work",
    "cordonnerie": "shoemaking", "vitrage": "glazing", "tissage": "weaving", "tapis à point noué": "knotted carpet",
    "dentelle": "lace", "bijouterie": "jewellery", "photographie": "photography", "sellerie": "saddlery", "gravure": "engraving",
    "mobilier": "furniture", "miroiterie": "mirror work", "glyptique": "gem engraving", "papier peint": "wallpaper",
    "parqueterie": "parquetry", "manuscrit": "manuscript", "décor stuqué": "stucco", "programme sculpté": "sculpted programme",
}

OWNERSHIP = {
    "propriété de la commune": "the commune", "propriété privée": "private owner", "propriété de l'état": "the State",
    "propriété d'une association": "an association", "propriété d'une société privée": "a private company",
    "propriété du département": "the département", "propriété d'une association cultuelle": "a religious association",
    "propriété d'un établissement public": "a public body", "propriété de la région": "the region",
    "propriété d'une association diocésaine": "a diocesan association", "propriété publique": "public owner",
    "propriété d'un établissement public de l'état": "a State public body", "propriété d'une personne privée": "private owner",
    "propriété d'une société privée ": "a private company",
}


def en(table, term):
    """English for a vocabulary term, or the French term unchanged when unknown."""
    return table.get(term.strip().lower().replace("’", "'"), table.get(term.strip(), term.strip()))


def owners(value):
    parts = [p.strip() for p in value.split(";") if p.strip()]
    out = []
    for p in parts:
        e = OWNERSHIP.get(p.lower().replace("’", "'"), p)
        if e not in out:
            out.append(e)
    return "; ".join(out)
