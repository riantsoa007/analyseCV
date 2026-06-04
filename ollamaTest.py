from ollama import chat

# L'historique stocke tous les messages de la conversation
historique = [
    {
        "role": "system",
        "content": """Tu es un assistant pédagogique pour des étudiants
        en informatique à l'ESTI. Tu réponds toujours en français,
        avec des exemples concrets et simples. Tu es patient et bienveillant."""
    }
]

print("=== Chatbot Ollama Local ===")
print("Tapez 'exit' pour quitter\n")

while True:
    # 1. Lire la question de l'utilisateur
    question = input("Vous : ")

    if question.lower() in ["exit", "quit", "bye"]:
        print("Au revoir !")
        break

    # 2. Ajouter le message de l'utilisateur à l'historique
    historique.append({
        "role": "user",
        "content": question
    })

    # 3. Envoyer TOUT l'historique au modèle
    #    (c'est comme ça que le modèle "se souvient")
    response = chat(
        model="qwen2.5:0.5b",
        messages=historique      # on envoie l'historique complet
    )

    # 4. Récupérer la réponse
    reponse_ia = response["message"]["content"]

    # 5. Ajouter la réponse de l'IA à l'historique
    historique.append({
        "role": "assistant",
        "content": reponse_ia
    })

    # 6. Afficher la réponse
    print(f"\nIA : {reponse_ia}\n")