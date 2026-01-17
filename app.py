import streamlit as st
from owlready2 import *
import os
ONTOLOGY_PATH = os.path.join(os.getcwd(), "ontologierecette.owl")
# Configuration de la page
st.set_page_config(
    page_title="Gestion de Recettes - Ontologie OWL",
    page_icon="🍳",
    layout="wide"
)

# Fonction pour charger l'ontologie depuis le fichier
@st.cache_resource
def load_ontology(file_path):
    """Charge l'ontologie OWL depuis le fichier fourni"""
    try:
        onto = get_ontology(f"file://{file_path}").load()
        return onto
    except Exception as e:
        st.error(f"Erreur lors du chargement de l'ontologie : {e}")
        return None

def initialize_default_data(onto):
    """Initialise l'ontologie avec des données par défaut"""
    
    # Vérifier si des données existent déjà
    if len(list(onto.Ingredient.instances())) > 0:
        return
    
    with onto:
        # Création des ingrédients par défaut
        poulet = onto.Viande("Poulet")
        saumon = onto.ProduitMarin("Saumon")
        lait = onto.ProduitLaitier("Lait")
        fromage = onto.ProduitLaitier("Fromage")
        
        
        tomate = onto.Fruit("Tomate")
        banane = onto.Fruit("Banane")
        pomme = onto.Fruit("Pomme")
        
        riz = onto.Cereale("Riz")
        farine = onto.CerealeAvecGluten("Farine")
        pain = onto.CerealeAvecGluten("Pain")
        
        lentilles = onto.Legumineuse("Lentilles")
        pois_chiches = onto.Legumineuse("PoisChiches")
        
        amandes = onto.Oleagineux("Amandes")
        
        # Création des recettes par défaut
        poulet_roti = onto.Recette("PouletRoti")
        poulet_roti.aPourIngredient = [poulet, tomate]
        
        salade_lentilles = onto.Recette("SaladeLentilles")
        salade_lentilles.aPourIngredient = [lentilles, tomate, pomme]
        
        gateau_chocolat = onto.Recette("GateauChocolat")
        gateau_chocolat.aPourIngredient = [farine, lait, fromage]
        
        saumon_grille = onto.Recette("SaumonGrille")
        saumon_grille.aPourIngredient = [saumon, riz]
        
        curry_pois_chiches = onto.Recette("CurryPoisChiches")
        curry_pois_chiches.aPourIngredient = [pois_chiches, tomate, riz]

def get_ingredient_category(ingredient, onto):
    """Retourne la catégorie d'un ingrédient"""
    if isinstance(ingredient, onto.Viande):
        return "Viande"
    elif isinstance(ingredient, onto.ProduitMarin):
        return "ProduitMarin"
    elif isinstance(ingredient, onto.ProduitLaitier):
        return "ProduitLaitier"
    elif isinstance(ingredient, onto.Oeuf):
        return "Oeuf"
    elif isinstance(ingredient, onto.CerealeAvecGluten):
        return "CerealeAvecGluten"
    elif isinstance(ingredient, onto.Cereale):
        return "Cereale"
    elif isinstance(ingredient, onto.Fruit):
        return "Fruit"
    elif isinstance(ingredient, onto.Legumineuse):
        return "Legumineuse"
    elif isinstance(ingredient, onto.Oleagineux):
        return "Oleagineux"
    else:
        return "Autre"

# ----------------- Ajout de la logique de clôture (closure axioms) -----------------
def remove_existing_aPourIngredient_closure(recette, onto):
    """Supprime les restrictions individuelles existantes sur aPourIngredient pour l'individu"""
    # on itère sur une copie car on modifie la liste
    for ax in list(recette.is_a):
        # Un axiome de restriction a un attribut 'property' dans owlready2
        try:
            if isinstance(ax, Restriction) and ax.property == onto.aPourIngredient:
                # retirer cette restriction
                recette.is_a.remove(ax)
        except Exception:
            # si l'axiome n'est pas une restriction ou n'a pas property, on ignore
            pass

def apply_closure_to_recipe(recette, onto):
    """
    Applique un axiome de clôture du type:
      recette.is_a += [ aPourIngredient only OneOf([ing1,ing2,...]) ]
    Ceci indique explicitement que tous les fillers connus pour aPourIngredient
    sont exactement ces individus (fermeture locale).
    """
    ingredients = list(recette.aPourIngredient)
    # supprimer les anciennes clôtures pour éviter empilement
    remove_existing_aPourIngredient_closure(recette, onto)
    if not ingredients:
        return False
    # créer une énumération (OneOf) des individus ingrédients
    try:
        enumeration = OneOf(ingredients)
        restriction = onto.aPourIngredient.only(enumeration)
        # ajouter la restriction dans is_a de l'individu (assertion individuelle)
        recette.is_a.append(restriction)
        return True
    except Exception as e:
        # si erreur, on ignore et retourne False
        print(f"Erreur apply_closure_to_recipe: {e}")
        return False

def apply_closure_to_all_recipes(onto):
    """Applique la clôture à toutes les recettes présentes dans l'ontologie"""
    count = 0
    for recette in list(onto.Recette.instances()):
        if apply_closure_to_recipe(recette, onto):
            count += 1
    return count

# ----------------- Raisonnement & inférences -----------------
def run_reasoner_and_get_types(onto, apply_closure_before_reasoning=False):
    """Lance le raisonneur OWL pour inférer les types de recettes."""
    try:
        apply_closure_to_all_recipes(onto)
        with onto:
            sync_reasoner_pellet(infer_property_values=True, infer_data_property_values=True)
        return True
    except Exception as e:
        st.warning(f"Le raisonneur n'a pas pu être exécuté : {e}")
        return False

def get_inferred_types(recette, onto):
    """Récupère les types inférés d'une recette après raisonnement"""
    types = []
    
    # Vérifier les types inférés par le raisonneur
    if isinstance(recette, onto.RecetteCarnee):
        types.append("🥩 Carnée")
    if isinstance(recette, onto.RecetteVegane):
        types.append("🌱 Végane")
    if isinstance(recette, onto.RecetteVegetarienne):
        types.append("🥗 Végétarienne")
    if isinstance(recette, onto.RecetteSansGluten):
        types.append("🌾 Sans Gluten")
    
    # Si aucun type n'est inféré, faire une inférence manuelle simple (fallback)
    if not types:
        ingredients = list(recette.aPourIngredient)
        has_animal = any(isinstance(ing, onto.ProduitAnimal) for ing in ingredients)
        has_meat_or_fish = any(isinstance(ing, (onto.Viande, onto.ProduitMarin)) for ing in ingredients)
        has_meat = any(isinstance(ing, onto.Viande) for ing in ingredients)
        has_gluten = any(isinstance(ing, onto.CerealeAvecGluten) for ing in ingredients)
        
        if has_meat:
            types.append("🥩 CarnéeL")
        if not has_animal:
            types.append("🌱 VéganeL")
        if not has_meat_or_fish:
            types.append("🥗 VégétarienneL")
        if not has_gluten:
            types.append("🌾 Sans GlutenL")
    
    return types

def check_compatibility(recette, profile_name, onto):
    """Vérifie si une recette est compatible avec un profil"""
    ingredients = list(recette.aPourIngredient)
    
    if profile_name == "Vegetarien":
        return not any(isinstance(ing, (onto.Viande, onto.ProduitMarin)) for ing in ingredients)
    elif profile_name == "Vegane":
        return not any(isinstance(ing, onto.ProduitAnimal) for ing in ingredients)
    elif profile_name in ["SansGluten", "AllergieGluten"]:
        return not any(isinstance(ing, onto.CerealeAvecGluten) for ing in ingredients)
    elif profile_name == "AllergieLactose":
        return not any(isinstance(ing, onto.ProduitLaitier) for ing in ingredients)
    elif profile_name == "AllergieArachide":
        return not any(isinstance(ing, onto.Oleagineux) and "arachide" in ing.name.lower() 
                      for ing in ingredients)
    return True

def save_ontology(onto, file_path):
    """Sauvegarde l'ontologie dans le fichier"""
    try:
        onto.save(file=file_path)
        return True
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde : {e}")
        return False

# CSS personnalisé
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #ff6b35 0%, #dc3545 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
    .recipe-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #ff6b35;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .ingredient-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        background: #e8f5e9;
        color: #2e7d32;
        border-radius: 15px;
        margin: 0.25rem;
        font-size: 0.9rem;
    }
    .type-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        background: #e3f2fd;
        color: #1976d2;
        border-radius: 15px;
        margin: 0.25rem;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

# En-tête
st.markdown("""
<div class="main-header">
    <h1>🍳 Gestion de Recettes - Ontologie OWL</h1>
    <p>Gérez vos recettes avec classification intelligente basée sur OWL</p>
</div>
""", unsafe_allow_html=True)

# Chargement du fichier OWL
st.sidebar.header("⚙️ Configuration")


# Charger l'ontologie depuis un fichier fixe
onto = load_ontology(ONTOLOGY_PATH)

if onto is None:
    st.error("Impossible de charger l'ontologie à partir de ontologierecette.owl")
    st.stop()
 
apply_closure_to_all_recipes(onto)
temp_path = os.path.join(os.getcwd(), "temp_ontology.owl")
save_ontology(onto, temp_path)

# Initialiser avec des données par défaut si l'ontologie est vide
if st.sidebar.button("📊 Initialiser avec des données par défaut"):
    initialize_default_data(onto)
    save_ontology(onto, temp_path)
    st.sidebar.success("Données par défaut ajoutées!")
    st.rerun()


# Bouton pour lancer le raisonneur
if st.sidebar.button("🧠 Lancer le raisonneur (inférence OWL)"):
    with st.spinner("Inférence en cours..."):
        if run_reasoner_and_get_types(onto):
            save_ontology(onto, temp_path)
            st.sidebar.success("✅ Raisonnement terminé!")
            st.rerun()


# Navigation par onglets
tab1, tab2, tab4 = st.tabs(["📖 Recettes", "🥬 Ingrédients", "🔍 Filtrage"])

# ==================== ONGLET RECETTES ====================
with tab1:
    st.header("📖 Gestion des Recettes")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader(f"Liste des recettes ({len(list(onto.Recette.instances()))})")
    
    with col2:
        if st.button("➕ Ajouter une recette", use_container_width=True):
            st.session_state.show_add_recipe = True
    
    # Formulaire d'ajout de recette
    if st.session_state.get('show_add_recipe', False):
        with st.form("add_recipe_form"):
            st.subheader("Nouvelle Recette")
            recipe_name = st.text_input("Nom de la recette")
            
            ingredients_list = list(onto.Ingredient.instances())
            selected_ingredients = st.multiselect(
                "Sélectionner les ingrédients",
                options=[ing.name for ing in ingredients_list],
                help="Sélectionnez un ou plusieurs ingrédients"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                submit = st.form_submit_button("💾 Enregistrer", use_container_width=True)
            with col2:
                cancel = st.form_submit_button("❌ Annuler", use_container_width=True)
            
            if submit and recipe_name and selected_ingredients:
                with onto:
                    # Créer un nom sans espaces pour l'instance
                    instance_name = recipe_name.replace(" ", "").replace("'", "").replace("-", "")
                    new_recipe = onto.Recette(instance_name)
                    
                    # Ajouter les ingrédients
                    for ing_name in selected_ingredients:
                        ingredient = next((ing for ing in ingredients_list if ing.name == ing_name), None)
                        if ingredient:
                            new_recipe.aPourIngredient.append(ingredient)
                    
                    # appliquer la clôture automatiquement si activée
                    apply_closure_to_recipe(new_recipe, onto)
                
                save_ontology(onto, temp_path)
                st.success(f"✅ Recette '{recipe_name}' ajoutée avec succès!")
                st.session_state.show_add_recipe = False
                st.rerun()
            
            if cancel:
                st.session_state.show_add_recipe = False
                st.rerun()
    
    # Barre de recherche
    search_term = st.text_input("🔎 Rechercher une recette", "")
    
    # Affichage des recettes
    recettes = list(onto.Recette.instances())
    
    if search_term:
        recettes = [r for r in recettes if search_term.lower() in r.name.lower()]
    
    for recette in recettes:
        with st.container():
            col1, col2 = st.columns([5, 1])
            
            with col1:
                st.markdown(f"### {recette.name}")
                
                # Affichage des ingrédients
                ingredients = list(recette.aPourIngredient)
                if ingredients:
                    st.markdown("**Ingrédients:** " + ", ".join([ing.name for ing in ingredients]))
                
                # Affichage des types inférés
                types = get_inferred_types(recette, onto)
                if types:
                    st.markdown("**Types:** " + " ".join([f"`{t}`" for t in types]))
            
            with col2:
                if st.button("🗑️", key=f"del_recipe_{recette.name}"):
                    destroy_entity(recette)
                    save_ontology(onto, temp_path)
                    st.rerun()
            
            st.divider()

# ==================== ONGLET INGREDIENTS ====================
with tab2:
    st.header("🥬 Gestion des Ingrédients")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader(f"Liste des ingrédients ({len(list(onto.Ingredient.instances()))})")
    
    with col2:
        if st.button("➕ Ajouter un ingrédient", use_container_width=True):
            st.session_state.show_add_ingredient = True
    
    # Formulaire d'ajout d'ingrédient
    if st.session_state.get('show_add_ingredient', False):
        with st.form("add_ingredient_form"):
            st.subheader("Nouvel Ingrédient")
            ing_name = st.text_input("Nom de l'ingrédient")
            
            category = st.selectbox(
                "Catégorie",
                ["Viande", "ProduitMarin", "ProduitLaitier", "Oeuf", 
                 "Fruit", "Cereale", "CerealeAvecGluten", "Legumineuse", "Oleagineux"]
            )
            
            col1, col2 = st.columns(2)
            with col1:
                submit = st.form_submit_button("💾 Enregistrer", use_container_width=True)
            with col2:
                cancel = st.form_submit_button("❌ Annuler", use_container_width=True)
            
            if submit and ing_name and category:
                with onto:
                    instance_name = ing_name.replace(" ", "").replace("'", "").replace("-", "")
                    category_class = getattr(onto, category)
                    new_ingredient = category_class(instance_name)
                
                save_ontology(onto, temp_path)
                st.success(f"✅ Ingrédient '{ing_name}' ajouté avec succès!")
                st.session_state.show_add_ingredient = False
                st.rerun()
            
            if cancel:
                st.session_state.show_add_ingredient = False
                st.rerun()
    
    # Affichage par catégories
    categories = {
        "🥩 Viande": onto.Viande,
        "🐟 Produits Marins": onto.ProduitMarin,
        "🥛 Produits Laitiers": onto.ProduitLaitier,
        "🥚 Œufs": onto.Oeuf,
        "🍎 Fruits": onto.Fruit,
        "🌾 Céréales": onto.Cereale,
        "🌾 Céréales avec Gluten": onto.CerealeAvecGluten,
        "🫘 Légumineuses": onto.Legumineuse,
        "🥜 Oléagineux": onto.Oleagineux
    }
    
    for cat_name, cat_class in categories.items():
        instances = list(cat_class.instances())
        if instances:
            st.subheader(f"{cat_name} ({len(instances)})")
            
            cols = st.columns(4)
            for idx, ing in enumerate(instances):
                with cols[idx % 4]:
                    col_ing, col_del = st.columns([4, 1])
                    with col_ing:
                        st.markdown(f"**{ing.name}**")
                    with col_del:
                        if st.button("🗑️", key=f"del_ing_{ing.name}_{idx}"):
                            destroy_entity(ing)
                            save_ontology(onto, temp_path)
                            st.rerun()
            st.divider()

# ==================== ONGLET FILTRAGE ====================
with tab4:
    st.header("🔍 Filtrage par Profil Alimentaire")
    
    profile_filter = st.selectbox(
        "Sélectionner un profil alimentaire",
        ["Tous"] + ["Vegetarien","Vegane", "SansGluten",]
    )
    
    recettes = list(onto.Recette.instances())
    
    if profile_filter != "Tous":
        compatible_recipes = [r for r in recettes if check_compatibility(r, profile_filter, onto)]
        st.info(f"🔎 {len(compatible_recipes)} recette(s) compatible(s) avec le profil **{profile_filter}**")
        recettes = compatible_recipes
    
    # Affichage des recettes filtrées
    for recette in recettes:
        with st.container():
            st.markdown(f"### {recette.name}")
            
            # Affichage des ingrédients
            ingredients = list(recette.aPourIngredient)
            if ingredients:
                st.markdown("**Ingrédients:** " + ", ".join([ing.name for ing in ingredients]))
            
            # Affichage des types inférés
            types = get_inferred_types(recette, onto)
            if types:
                st.markdown("**Types:** " + " ".join([f"`{t}`" for t in types]))
            
            st.divider()

# Pied de page
st.markdown("---")
st.markdown("💡 **Astuce:** Utilisez le bouton '🧠 Lancer le raisonneur' dans la barre latérale pour inférer automatiquement les types de recettes selon l'ontologie OWL!")
