# Projet de reconnaissance visuelle et de pilotage d’un jeu Windows

Document de cadrage — version 6, 15 octobre 2026. Intègre la lecture du dépôt, les combos avec adaptation spatiale, la détection des tours, le contrôle de plusieurs personnages et la correction des démonstrations après combat. Examen statique du commit 019d2571e552b345a7d85a15901f043b46c30d57 ; aucune exécution du jeu ni mesure de performance effectuée ici.

## 1. Objectif

Développer un système capable d’observer Wakfu, jeu en tour par tour, exécuté sous Windows, de combiner reconnaissance visuelle et informations issues des logs, puis de sélectionner et faire exécuter des combos de compétences dans un ordre défini. L’IA choisira parmi des combos existants et adaptera leur orientation et leurs cibles à la disposition réelle des monstres, qui peuvent échanger leurs positions d’un combat à l’autre.

Le développement principal et les traitements d’intelligence artificielle seront réalisés sous WSL 2. Les services Linux seront conteneurisés et orchestrés avec Docker Compose. L’architecture devra permettre de déplacer ces services vers une autre machine sans réécrire la logique de reconnaissance ou de décision.

Le fonctionnement reposera sur des captures périodiques, avec un intervalle initial visé d’environ une seconde, configurable. Le terme « vague » employé pour le projet désigne ces cycles d’observation et de traitement.

Trois briques existent déjà et devront être intégrées : un modèle YOLO entraîné pour reconnaître les monstres ; un projet lisant les logs et fournissant leur nombre, leur type et leurs coordonnées dans le jeu ; un projet capable de contrôler le PC. Le nouveau travail porte principalement sur leurs interfaces, la consolidation de l’état, la sélection des combos et leur orchestration.

## 2. Architecture fonctionnelle

Le système comprend les composants logiques suivants. Ils pourront être regroupés dans certains processus pour le prototype, mais leurs interfaces devront rester explicites.

| Composant | Emplacement initial | Responsabilités |
| --- | --- | --- |
| Agent Windows | Windows, application native | Capturer la fenêtre du jeu et adapter le projet existant de contrôle du PC ; recevoir les commandes et renvoyer leur résultat |
| Adaptateur de logs | Lecture sous Windows ; parsing sous WSL proposé | Transmettre les nouvelles lignes au serveur, réutiliser le parseur et exposer les données avec horodatage |
| Passerelle de communication | Conteneur Linux sous WSL | Gérer les connexions, identifier les sessions, valider les messages et coordonner les cycles |
| Service de perception | Conteneur Linux sous WSL | Exécuter le modèle YOLO existant ; produire des détections et positions à l’écran avec leurs scores de confiance |
| Gestionnaire d’état | Service Linux | Rapprocher logs et détections, suivre les monstres et leur état K.O., conserver l’historique |
| Moteur de décision | Conteneur Linux sous WSL | Choisir un combo et ses cibles en fonction de la situation et suivre son exécution ordonnée |

La séparation entre perception, état et décision permettra de remplacer un modèle sans modifier l’agent Windows.

L’agent Windows restera natif : il doit accéder à la fenêtre du jeu et aux entrées clavier/souris de la session Windows. Docker Compose pilotera les services Linux, pas le jeu ni cet agent.

## 3. Déroulement d’un cycle

1. L’agent capture la zone du jeu et lui attribue un identifiant de session, un numéro de capture, un horodatage et les dimensions de l’image.
2. Il transmet l’image et ses métadonnées au serveur. L’adaptateur de logs publie les informations du jeu disponibles, à leur propre cadence.
3. Le service de perception analyse la capture et produit des observations structurées.
4. Le gestionnaire d’état rapproche ces observations des précédentes et des logs, puis publie une nouvelle version de l’état du jeu.
5. En mode AI_CONTROL, si c’est le tour d’un personnage contrôlé et qu’aucun combo n’est déjà en cours, le moteur de décision utilise cet état pour choisir un combo et ses cibles. Le tour est reconnu à partir de la barre d’initiative à droite, avec identification du participant actif. En mode HUMAN_CONTROL, perception et suivi continuent, mais aucune commande de jeu de l’IA n’est exécutée.
6. La passerelle valide la commande et la transmet à l’agent Windows.
7. L’agent vérifie ses conditions d’exécution, applique la commande et renvoie un accusé de réception puis un résultat.
8. Une nouvelle capture permet de vérifier l’effet réel de l’action, d’actualiser les monstres K.O. et de poursuivre, terminer ou interrompre le combo.

Une commande exécutée avec succès signifie que les entrées ont été envoyées. Seule une observation ultérieure permet de confirmer leur effet dans le jeu.

## 4. Reconnaissance et suivi des monstres

Chaque observation devra fournir, lorsque l’information est disponible :

- La catégorie ou le type de monstre détecté.
- Son type ou nom, selon les classes du modèle et les informations des logs ; la lecture de texte n’est pas un prérequis du prototype.
- Sa boîte de détection et son point de ciblage dans l’image.
- Un score de confiance associé à chaque prédiction utile.
- Sa présence ou son absence par rapport aux observations précédentes du même combat.

Le gestionnaire d’état réutilisera l’identifiant d’entité des logs, associé au combat, lorsque le rapprochement avec YOLO est possible. Sinon, il attribuera un identifiant de suivi visuel provisoire, distinct de sa catégorie et de son nom. Ce suivi sera estimé et pourra être incertain en cas d’occlusion, de déplacement de caméra ou de monstres semblables.

Règle fonctionnelle retenue à la demande de l’utilisateur : un monstre précédemment suivi qui disparaît d’une nouvelle observation exploitable est considéré K.O. Pour le prototype, une seule disparition suffit ; aucune analyse d’animation de mort ni confirmation sur plusieurs images n’est requise.

Une capture manquante, invalide ou une panne d’inférence ne constitue pas une observation de disparition. L’état K.O. sera conservé dans l’historique du combat et réinitialisé au début du combat suivant. La gestion d’une éventuelle réapparition reste à définir selon les mécaniques du jeu.

Deux systèmes de coordonnées seront conservés séparément : les coordonnées `game_x`, `game_y` issues des logs et les coordonnées à l’écran issues de YOLO. Le type et les positions d’entrée en combat seront repris du lecteur de logs ; YOLO apportera la présence visuelle et les positions à l’écran. Le parseur examiné ne met pas à jour les positions après déplacement. Un horodatage récent de lecture ne rendra pas une position initiale courante. Le nombre d’ennemis actifs sera calculé à partir de l’état consolidé. Les désaccords entre sources seront explicitement signalés ; les logs ne réactiveront pas automatiquement un monstre marqué K.O. par la règle de disparition.

La correspondance entre une entité des logs et une détection visuelle devra être définie, notamment pour plusieurs monstres du même type. La classe existante IsoCoordinateMapper fournit une base de projection x/y vers l’écran. Son calibrage et les changements de caméra devront être validés ; la projection actuelle n’utilise pas z. Le centre d’une boîte YOLO ne sera pas présupposé être le centre de la case occupée. Le passage au clic Windows tiendra compte de la position de la fenêtre, de sa résolution, de la zone capturée et de la mise à l’échelle de l’affichage.

## 5. État du jeu et fraîcheur des informations

Chaque état publié comprendra :

| Groupe | Informations principales |
| --- | --- |
| Identification | Version du protocole, session, combat, tour si disponible, capture source, version de l’état |
| Temps | Instant de capture, réception et fin de traitement ; durées des étapes |
| Entités | Identifiant de suivi, nom/type, coordonnées de jeu et d’écran, état actif/K.O., confiance, source |
| Historique | Première observation, dernière observation et dernier changement d’état |
| Contexte | Ordre d’initiative, participant actif, personnage contrôlé, numéro de tour si lisible, phase du combat et ressources disponibles |
| Exécution | Mode humain/IA, enregistrement actif ou non, génération de contrôle, combo et étape en cours, cible, dernier résultat reçu |
| Validité | État exploitable, incertain ou trop ancien |

Un affichage de diagnostic présentera le temps écoulé depuis la dernière capture reçue, la dernière information de logs, le dernier état calculé et la dernière observation de chaque monstre. Ces compteurs continueront à progresser même si aucune nouvelle donnée n’arrive. Images et logs garderont leurs propres horodatages pour ne pas présenter des informations anciennes comme simultanées.

Les horodatages UTC serviront à la traçabilité. Les délais d’expiration et mesures locales utiliseront une horloge monotone. Avec un serveur distant, la synchronisation des horloges ou une estimation de leur décalage sera nécessaire pour mesurer correctement l’âge de bout en bout.

## 6. Décisions et commandes

Le moteur de décision recevra l’état structuré du jeu et un catalogue de combos. Chaque combo définira un identifiant, une liste ordonnée de compétences, les règles de ciblage, les délais ou confirmations entre étapes et les conditions d’arrêt. Les préconditions pourront inclure le tour du joueur, les ressources, la portée et la disponibilité d’une compétence si ces informations sont accessibles.

L’IA choisira parmi les combos prédéfinis et adaptera leurs paramètres : orientation Nord/Sud/Est/Ouest, cibles et éventuelles cases de placement. Un exécuteur déterministe fera respecter l’ordre des compétences. Le choix du modèle ou de l’algorithme de sélection reste ouvert ; la génération libre de nouveaux combos ne fait pas partie du prototype.

Il produira des commandes conformes à un schéma fermé, par exemple : cliquer à une position, appuyer sur une touche pendant une durée bornée, attendre, annuler une séquence ou ne rien faire. Il ne produira pas de code arbitraire à exécuter.

Chaque commande comprendra un identifiant unique, la session concernée, l’état ayant motivé la décision, son type, ses paramètres et une durée de validité. Une séquence pourra préciser les conditions de passage à l’étape suivante et les conditions d’annulation.

L’agent Windows devra :

- Refuser les commandes expirées, invalides ou appartenant à une ancienne session.
- Éviter de rejouer une commande déjà exécutée après une reconnexion.
- Vérifier que la fenêtre attendue est active et que les coordonnées sont encore valides.
- Libérer les touches et boutons maintenus lors d’une interruption ou d’une déconnexion.
- Permettre une pause et un arrêt immédiat par l’utilisateur.

Un seul combo sera actif à la fois. Les observations continueront pendant son exécution sans déclencher une seconde copie du combo chaque seconde. L’exécuteur suivra les états `pending`, `running`, `completed`, `failed` et `cancelled`, ainsi que l’étape courante. Un accusé de réception des entrées ne remplacera pas une éventuelle confirmation de leur effet dans le jeu.

Les délais entre compétences seront indépendants de l’intervalle de capture. La fin du tour, une cible K.O., une erreur, une reprise humaine ou un état trop ancien pourront interrompre la suite, selon les règles du combo. Le choix entre changement de cible et arrêt après un K.O. reste à préciser.

## 7. Cadence et gestion des retards

L’intervalle de capture initial visé sera d’environ une seconde, configurable indépendamment du temps de traitement et de la vitesse d’exécution des compétences. Pour le prototype, un seul traitement de perception et une seule décision seront actifs à la fois ; seule la capture en attente la plus récente sera conservée.

Les captures intermédiaires pourront être abandonnées si le traitement prend du retard. Le système ne devra pas accumuler une file d’images anciennes puis agir sur celles-ci.

Des seuils configurables définiront la durée maximale d’un traitement, l’âge maximal d’un état utilisable, la validité d’une commande et le délai avant déclaration d’une perte de connexion. Si ces seuils sont dépassés, le système suspendra les actions et demandera une observation récente.

L’objectif est de reconnaître la situation environ chaque seconde, puis de lancer ou superviser un combo. Cette cadence est un objectif à mesurer sur la machine cible, pas une performance déjà démontrée. Le système n’enverra pas automatiquement une nouvelle compétence à chaque capture.

## 8. Communication et déplacement vers un serveur distant

Le protocole applicatif sera indépendant de WSL et des chemins de fichiers locaux. Proposition initiale : une connexion WebSocket ouverte par l’agent Windows, avec messages JSON versionnés pour les états, commandes et résultats, et transfert binaire des images associé explicitement à leur identifiant de capture.

Les messages couvriront au minimum la connexion initiale, les captures, les états, les commandes, les accusés de réception, les résultats, les erreurs et les signaux de présence. La taille des images et les paramètres reçus seront validés.

L’adresse du serveur, les ports, les délais et l’authentification seront configurables. En local, Windows pourra joindre les services WSL par un port publié accessible via `localhost`, selon la configuration réseau. Sur une autre machine, la même interface utilisera son adresse réseau, avec authentification et chiffrement adaptés.

Un câble Ethernet permet de conserver cette architecture IP. Une liaison USB devra être précisée : elle peut conserver le même protocole si le matériel expose une interface réseau ; une liaison série ou un autre transport nécessitera un adaptateur de communication. Un câble USB quelconque entre deux ordinateurs ne constitue donc pas une solution définie à ce stade.

## 9. Docker et Docker Compose

Le projet fournira les Dockerfiles, un fichier `compose.yaml`, un exemple de configuration et les instructions de démarrage.

La composition initiale pourra regrouper quatre services : `gateway` pour la communication, la consolidation des sources et la coordination ; `log-reader` pour le parseur et l’API FastAPI ; `perception` pour YOLO ; `decision` pour la sélection et le suivi des combos. Pour permettre le déplacement du serveur, Windows lira les nouvelles lignes du fichier et les transmettra à la passerelle, qui les remettra au parseur sous WSL. Une interface d’ingestion devra être ajoutée au lecteur existant. Le serveur ne dépendra pas d’un montage du disque Windows. Les composants logiques resteront séparés dans le code.

Les services internes utiliseront le réseau Compose ; seul le point d’entrée nécessaire à l’agent sera publié. Des volumes conserveront les modèles, configurations et journaux utiles. Les contrôles de santé et les politiques de redémarrage seront définis ; un redémarrage invalidera les commandes antérieures.

Matériel disponible : AMD Ryzen 7 PRO 4750U, 16 Go de RAM, circuit graphique intégré AMD Radeon, environnement Windows x64. La première configuration proposée utilisera l’inférence sur CPU afin de disposer d’une base de mesure sans présumer d’une accélération GPU compatible. Le détecteur existant utilise YOLOv4-tiny au format Darknet, via OpenCV DNN, avec une entrée 416 × 416 par défaut. Cette base sera conservée pour le prototype.

Le temps d’inférence et la consommation mémoire seront mesurés avec le jeu et les services actifs. Les images seront traitées sans accumulation et leur archivage sera limité ou désactivé par défaut. L’IA de décision devra également respecter le budget matériel ; un gros modèle local n’est pas présupposé. Le choix entre Docker Desktop avec intégration WSL et un moteur Docker dans WSL sera documenté.

## 10. Périmètre et validation du prototype

Le premier prototype ciblera un combat reproductible, une configuration d’affichage et un combo décrit précisément. Il réutilisera les trois projets existants avant d’envisager de nouveaux entraînements ou une réécriture.

| Étape | Résultat attendu |
| --- | --- |
| Acquisition | Captures Windows reçues et correctement identifiées par le serveur |
| Perception | Modèle YOLO existant chargé et évalué sur des captures représentatives |
| Logs | Nombre, type, coordonnées et horodatages reçus via l’adaptateur |
| Suivi | Monstres rapprochés entre sources et marqués K.O. lors d’une disparition observée |
| Décision en simulation | Commandes enregistrées et examinables sans envoyer d’entrées au jeu |
| Boucle complète | Un combo exécuté une seule fois dans l’ordre défini, avec suivi de chaque étape |
| Robustesse | Gestion des retards, doublons, changements de fenêtre et déconnexions |
| Portabilité | Même agent connecté à une autre adresse serveur sans modification de logique |

Les mesures incluront la qualité des détections existantes, la cohérence logs/vision, la stabilité du suivi, la latence de bout en bout, la charge CPU/RAM et le respect de l’ordre des compétences. Le benchmark déterminera si l’objectif d’environ une seconde est atteint et quels ajustements sont nécessaires.

Les cas de validation couvriront aussi : deux monstres de même type, disparition de la cible au milieu d’un combo, fin de tour, observation reçue pendant un combo, logs anciens, perte de connexion et absence de double exécution après reconnexion.

## 11. Intégration des briques existantes et adaptation des combos

Dépôt examiné : [Tochimizu/Wakfu_complete_pipeline](https://github.com/Tochimizu/Wakfu_complete_pipeline), commit 019d2571e552b345a7d85a15901f043b46c30d57. Les constats suivants portent sur les fichiers publiés ; les versions locales peuvent différer.

### Briques réutilisables

| Brique | Constat dans le code | Travail d’intégration |
| --- | --- | --- |
| Clicker | Python, PyAutoGUI/Win32 ; perform_action et run_bot ; fichiers de touches, clics, coordonnées et délais | Importer les séquences, définir les cibles variables, ajouter annulation et résultats structurés |
| Logs | Python/FastAPI ; API /state et /state/{fight_id} ; identifiants de combat et d’entité, nom, breed, position x/y/z | Ajouter ingestion des lignes Windows, horodatages et événements manquants |
| Vision | YoloDetector et détections structurées ; capture Win32 séparée | Garder la capture sous Windows et déployer l’inférence sous Linux |

Le parseur actuel traite les lignes d’entrée en combat « join the fight at ». Il ne traite pas les déplacements, les changements de tour, les ressources ou la clôture du combat. Le nombre d’entités stockées peut inclure des joueurs et ne constitue pas un compteur d’ennemis vivants. La règle allié/ennemi devra être définie : isAI ne sera pas supposé suffire à identifier tous les ennemis. PvEEngine.on_state_update est encore un point d’extension vide.

Le point d’entrée du lecteur utilise un fichier de test. La découverte du chemin des logs, indiquée comme existante par l’utilisateur, devra être raccordée ; ce point d’entrée ne la démontre pas. Le suivi du fichier commence au début : le raccordement devra éviter de confondre des combats historiques avec le combat actif, et gérer rotation/troncature du fichier.

Le script de lancement du clicker utilise une boucle fixe de répétition. L’agent réutilisera ses fonctions sans lancer cette boucle pour chaque commande. Les erreurs actuellement imprimées par perform_action devront devenir des résultats exploitables par l’orchestrateur.

Les poids entraînés yolov4-tiny-custom_last.weights ne figurent pas dans l’arborescence examinée. Le notebook prévoit leur copie depuis Google Drive. Le fichier yolov4-tiny.conv.29 présent est utilisé pour initialiser l’entraînement ; il ne remplace pas le modèle entraîné attendu. Les poids locaux devront être fournis au service par volume.

### Combos paramétrables

Les fichiers actuels serviront de matière première. Certaines séquences incluent l’entrée en combat et des clics d’interface : ces blocs devront être séparés des combos de compétences. Chaque action sera classée selon son ciblage : interface, joueur, ennemi, case du plateau ou position relative. Les coordonnées d’un bouton d’interface ne subiront pas la transformation spatiale du plateau.

Chaque combo définira son personnage/classe, sa phase de combat, son point de référence, ses orientations autorisées, l’ordre des compétences, le sélecteur de cible de chaque étape, les délais et les conditions d’arrêt. Les cibles pourront être une entité ou une case vide pour un sort de zone. Les règles ne dépendront pas de l’ordre des détections YOLO.

L’adaptation suivra ces étapes :

1. Choisir le combo candidat, par exemple le combo d’ouverture.
2. Déterminer le point de référence et l’orientation dans le repère du plateau.
3. Transformer les cases relatives selon la convention Nord/Sud/Est/Ouest définie.
4. Résoudre les cibles actuelles selon type, position et priorité, en tenant compte de leurs permutations entre combats.
5. Vérifier les contraintes disponibles : cible active, portée, ressources et case ciblable. Une contrainte non observable restera inconnue.
6. Projeter les cases vers l’écran et transmettre les actions au clicker.
7. Réévaluer les cibles variables aux étapes prévues, en conservant l’ordre des compétences.

Les rotations seront réalisées dans le repère logique avant la projection isométrique. Une rotation des pixels autour du centre de l’écran ne suffit pas. Le point de référence et la convention des directions restent à préciser.

Exemple illustratif : Ctrl+1 → clic sur une cible résolue → Ctrl+2 → clic sur une autre cible résolue. Les raccourcis et leur ordre restent identiques ; les coordonnées sont calculées selon la situation. Si deux monstres ont échangé leurs places, la sélection suit les priorités du combo. Le comportement si une cible devient K.O. reste à définir.

La validation couvrira les quatre orientations, les permutations de monstres, les ennemis de même type et les sorts visant une case vide.

### Performances et Rust

L’utilisateur rapporte que le modèle fonctionnait pendant le jeu sans charge excessive. La nouvelle architecture doit néanmoins être mesurée avec le jeu actif. Les mesures distingueront capture, encodage, transfert, prétraitement, inférence et décision.

Aucune réécriture Rust n’est prévue initialement. Le code délègue déjà l’inférence à OpenCV DNN ; changer le langage de l’orchestrateur ne démontre pas un gain sur cette étape. Une optimisation ou évolution du matériel sera décidée selon le coût mesuré de chaque étape.

## 12. Tours de jeu et fin de combat

### Observation de la barre d’initiative

L’utilisateur confirme que la GUI à droite donne l’ordre des participants et que le halo bleu désigne celui qui joue actuellement son tour. La détection du tour reposera donc sur la localisation de ce halo et l’identification du portrait associé. Le panneau rectangulaire situé en dessous décrit l’entité actuellement survolée par le curseur ; il ne désigne pas le participant actif. L’image fournie montre également le texte « Tour 1 » et un compteur de temps en bas à droite.

La reconnaissance de cette interface constitue une fonction nouvelle : le modèle YOLO existant n’est pas encore entraîné pour cela. Elle pourra utiliser un module dédié à cette zone ; l’entraînement d’un détecteur supplémentaire ou l’usage d’autres indices visuels sera décidé à partir d’exemples. Il n’est pas présupposé qu’un réentraînement complet de YOLO soit nécessaire.

Les sorties attendues sont : liste ordonnée des participants visibles, identité du participant actif, correspondance avec les personnages contrôlés, confiance et horodatage. L’ordre seul ne prouve pas à qui est le tour ; il faut reconnaître le marqueur d’activité et suivre ses changements. Le système devra distinguer les portraits semblables et les modifications de liste après K.O. La simple sélection d’un personnage ne devra pas être confondue avec son tour actif.

Le suivi de tour pourra prendre les états : attente, tour contrôlé, tour non contrôlé et inconnu. Une transition validée vers un tour contrôlé autorisera la sélection d’un combo ; les observations successives du même tour ne le relanceront pas. Tant que le participant actif n’est pas reconnu, le mode IA attendra une observation exploitable. La première version prendra en charge jusqu’à trois personnages accessibles depuis une même fenêtre Windows de Wakfu, avec un seul personnage commandé à un instant donné. La structure des identifiants et de la configuration permettra une extension jusqu’à six personnages répartis sur deux comptes, sans rendre cette extension nécessaire au prototype.

### Fin de combat

Deux indices sont disponibles selon l’utilisateur : absence d’ennemis encore actifs et apparition de loots dans les logs. Le parseur publié n’extrait pas encore ces événements de loot ; cette extension fait partie du travail prévu.

Le système distinguera : combat actif, fin présumée et fin confirmée. Quand tous les ennemis suivis sont K.O., il passera en fin présumée et cessera d’émettre des attaques. Les événements de loot associés au combat courant confirmeront ensuite la fin. Des logs historiques relus au démarrage, un loot d’un combat précédent ou des messages répétés ne devront pas clôturer le mauvais combat.

Cette règle suppose qu’une liste d’ennemis ait été établie pour le combat : une initialisation vide ou un échec de perception ne constitue pas une victoire. L’absence de logs de loot après disparition des ennemis laissera la fin présumée visible dans le widget, avec possibilité de validation humaine. La fin confirmée annulera les actions restantes et clôturera l’épisode enregistré.

### Gestion des personnages contrôlés

Un registre associera chaque personnage contrôlé à son identité dans le combat, son portrait ou ses caractéristiques de reconnaissance, son compte/client lorsque nécessaire, ses raccourcis et son catalogue de combos. Ces associations seront configurables ; elles ne dépendront pas uniquement de la place du portrait dans la liste, qui peut changer pendant le combat.

Le contrôleur partagera une seule file d’exécution pour le PC. Lorsque le halo passe sur un personnage du registre, l’orchestrateur choisira sa configuration et un combo adapté à son état. Lorsque le participant actif n’est pas contrôlé, il continuera d’observer sans envoyer d’actions.

Le prototype utilisera une seule fenêtre Windows pour les trois personnages : aucun changement de fenêtre ne sera nécessaire entre leurs tours. L’extension à six personnages utilisera deux fenêtres Windows, correspondant aux deux comptes. Chaque personnage sera associé explicitement à son client ; chaque capture, état et commande portera un identifiant de client/fenêtre. L’agent devra alors gérer l’activation de la fenêtre visée, vérifier son identité avant les entrées et conserver un calibrage par fenêtre. Une seule file d’exécution restera partagée pour le PC afin d’éviter des actions simultanées sur les deux clients. La capture et les informations de logs devront être rattachées au bon client, sans confondre les observations d’un même combat provenant des deux comptes. Ce routage entre deux fenêtres sera une extension ultérieure, pas une condition du prototype. Le passage d’un personnage à l’autre ne nécessitera pas de redémarrer les services ; la perte ou le changement de tour annulera les étapes devenues invalides.

Les états de ressources, combos disponibles, actions déjà effectuées et démonstrations resteront rattachés à chaque personnage. Le mode humain/IA sera initialement global pour le contrôleur du PC ; la prise en charge de modes différents par personnage pourra être ajoutée si elle devient utile.

## 13. Basculement du contrôle et widget

Le système proposera deux modes persistants : HUMAN_CONTROL et AI_CONTROL. Le changement de mode ne redémarrera ni l’agent Windows, ni les conteneurs, ni le lecteur de logs. Les captures, la perception et l’état du jeu continueront à fonctionner dans les deux modes.

| Mode | Qui agit sur le jeu ? | Comportement du serveur |
| --- | --- | --- |
| HUMAN_CONTROL | L’utilisateur | Observer, suivre l’état et éventuellement proposer des décisions sans les exécuter |
| AI_CONTROL | L’exécuteur de commandes IA | Sélectionner et superviser les combos autorisés |

Un widget côté Windows affichera le mode réellement appliqué par l’agent, l’état de connexion, la fraîcheur des observations, le personnage actif, le combo et l’étape en cours. Il comprendra le basculement humain/IA, une commande d’arrêt des actions et un bouton d’enregistrement indépendant avec indicateur visible. Le widget ne devra pas rester devant les informations du jeu ni faire perdre durablement son focus. Un raccourci configurable permettra également la reprise humaine sans chercher le widget.

Le passage vers HUMAN_CONTROL sera appliqué immédiatement par l’agent Windows, sans attendre un aller-retour serveur. Il annulera la file de commandes IA et la séquence en cours, puis relâchera les touches et boutons maintenus par l’automatisation. Un clic déjà envoyé ne pourra pas être annulé rétroactivement ; aucune étape suivante ne devra toutefois être lancée.

Chaque changement incrémentera une génération de contrôle. Les commandes porteront cette génération ; celles d’un ancien mode seront rejetées, même si elles arrivent tardivement. L’agent Windows sera l’autorité finale sur le droit d’exécuter. L’exécuteur n’acceptera qu’une seule séquence active ; les changements de mode seront journalisés et communiqués au serveur.

Le retour en AI_CONTROL demandera une observation récente et une nouvelle décision. Il ne reprendra pas automatiquement un ancien combo à son étape d’interruption, car l’utilisateur a pu modifier le jeu entre-temps. Si le tour actif ou la situation restent inconnus, le mode IA sera affiché en attente. Après déconnexion, les actions seront arrêtées et la reprise du contrôle IA sera explicite.

## 14. Démonstrations humaines et behaviour cloning

L’objectif est de constituer des épisodes de jeu permettant à une politique de décision d’imiter les choix de l’utilisateur : combo choisi, orientation, cibles et éventuelles adaptations. L’enregistrement prépare cet apprentissage ; il ne signifie pas qu’un modèle apprend automatiquement en direct dès l’activation du mode humain.

### Collecte synchronisée

L’enregistrement sera activable séparément du mode de contrôle. Il sera limité aux interactions utiles avec la fenêtre du jeu ; les clics sur le widget et les touches saisies dans d’autres applications ne feront pas partie des démonstrations. Les commandes injectées par l’automatisation seront identifiées séparément pour éviter de les prendre pour des actions humaines.

| Données | Contenu attendu |
| --- | --- |
| Épisode | Session, combat, personnage, mode et génération de contrôle |
| Observation | Capture référencée, état consolidé, événements de logs, horodatages et fraîcheur des sources |
| Action humaine | Touche ou combinaison, appui/relâchement, bouton souris, position, temps de début/fin |
| Action interprétée | Compétence, cible entité/case, combo et étape lorsqu’identifiables |
| Contexte spatial | Coordonnées écran et de jeu si disponibles, orientation, version du calibrage |
| Résultat | Observation suivante, cible K.O., fin de tour/combat, correction ou interruption |

La boucle d’observation d’environ une seconde sera conservée pour le suivi général. Pour l’apprentissage, elle sera complétée par des événements d’entrée horodatés précisément et un contexte visuel juste avant les actions significatives. Une capture prise uniquement après un clic ne doit pas être utilisée comme si elle précédait la décision. Un tampon court d’observations pourra fournir le contexte antérieur ; une capture supplémentaire avant l’action pourra être déclenchée si nécessaire. La fraîcheur réelle sera enregistrée et les exemples trop anciens pourront être exclus.

Les états utilisés comme entrée d’apprentissage seront ceux disponibles avant l’action, sans intégrer des résultats futurs. Le relevé détaillé des clics sera conservé pour l’exécution, mais les exemples destinés à la décision viseront de préférence des actions sémantiques : identifiant de combo, orientation et cibles. Une séquence inconnue pourra être marquée pour annotation plutôt que forcée dans un combo existant.

### Préparation et apprentissage

1. Réutiliser les combos existants comme catalogue initial.
2. Enregistrer des combats et reprises humaines, notamment plusieurs orientations et permutations de monstres.
3. Après chaque combat enregistré, proposer une relecture pour segmenter les séquences et nommer, corriger ou exclure les démonstrations. L’utilisateur a confirmé vouloir effectuer cette labellisation. Un raccourci pour marquer le début d’un combo pourra simplifier cette étape.
4. Construire les exemples observation → décision attendue ; conserver les épisodes IA séparés des démonstrations humaines validées.
5. Entraîner hors de la boucle de jeu une politique de sélection et de paramétrage des combos.
6. Évaluer sur des combats réservés, séparés par épisode plutôt que par captures voisines.
7. Vérifier d’abord les suggestions sans exécution, puis activer le contrôle IA avec reprise humaine disponible.

Le modèle de décision et le détecteur de la barre d’initiative sont deux apprentissages distincts : des clics humains ne remplacent pas les annotations nécessaires à l’identification du participant actif. L’entraînement pourra être réalisé sur une autre machine tout en conservant l’inférence et le contrôle dans l’architecture prévue.

Un outil de relecture et d’annotation des démonstrations, des formats exportables documentés et une configuration de conservation des images feront partie des livrables de la phase apprentissage. Le volume de données à conserver restera configurable compte tenu du stockage disponible.

### Relecture et correction après combat

La fin confirmée du combat clôturera l’épisode et le rendra disponible dans une file de relecture, accessible depuis le widget. L’annotation pourra être différée : elle ne bloquera pas les captures, les services ni le combat suivant. La collecte d’épisodes et leur validation resteront distinctes.

La relecture présentera la chronologie des observations et des entrées, regroupées par tour et par personnage. Pour chaque segment, l’utilisateur pourra :

- Ajuster le début et la fin du combo, puis lui attribuer un nom existant ou créer une nouvelle étiquette à examiner.
- Corriger le personnage, l’orientation, le point de référence et les cibles interprétées de chaque compétence.
- Indiquer si la séquence est un exemple à reproduire, une tentative échouée à exclure, ou une correction à revoir.
- Valider l’annotation ou laisser le segment en attente.

Les données brutes seront conservées séparément des annotations versionnées. Une correction d’intention ne modifiera pas les clics réellement exécutés : par exemple, une cible souhaitée différente de la cible cliquée sera enregistrée explicitement, sans présenter le clic erroné comme une démonstration correcte. Les exemples d’imitation utiliseront par défaut les séquences humaines validées comme reproductibles.

Les nouveaux labels de combos devront être reliés à une séquence et à des règles de ciblage avant de devenir des combos exécutables. La validation d’une annotation n’entraînera pas automatiquement le remplacement du modèle en cours ; entraînement, évaluation et activation d’une nouvelle version resteront des étapes identifiables.

### Validation du contrôle partagé et de la collecte

Les vérifications couvriront une reprise humaine au milieu d’un combo, l’arrivée tardive d’une ancienne commande, plusieurs basculements rapprochés, le retour IA après déplacement manuel, le comptage distinct des actions humaines et injectées, l’alignement temporel observation/action et la clôture d’un épisode à la fin du combat. Le widget devra continuer à permettre la reprise humaine même si le serveur ne répond plus. Les essais couvriront aussi l’alternance entre trois personnages sans mélange de combos, le rejet d’une commande destinée au personnage précédent et la relecture par personnage. Une correction d’annotation devra préserver les données brutes et exclure du jeu d’imitation les tentatives marquées comme non reproductibles.

## 15. Questions à trancher

1. Quel premier combo faut-il annoter et quelles cibles correspondent à ses étapes ? Que désignent Nord/Sud/Est/Ouest et quel est le point de référence ?
2. Si une cible devient K.O., faut-il réaffecter la prochaine compétence ou interrompre le combo ? Quelles priorités départagent les monstres ? Ces choix pourront être affinés pendant les essais.
3. Quels messages de loot permettent d’associer la fin au combat courant ? Existe-t-il une version locale du parseur plus complète ?
4. Les poids YOLO entraînés sont-ils disponibles localement ? La décision doit-elle fonctionner entièrement en local ?

## Références techniques

Sources du dépôt examinées :

- [Exécuteur clavier/souris](https://github.com/Tochimizu/Wakfu_complete_pipeline/blob/019d2571e552b345a7d85a15901f043b46c30d57/0_clicker_no_brain/src.py) et [séquence Bilbiza](https://github.com/Tochimizu/Wakfu_complete_pipeline/blob/019d2571e552b345a7d85a15901f043b46c30d57/0_clicker_no_brain/steps_Bilbiza/1_new_Bilbi_run.txt).
- [Parseur](https://github.com/Tochimizu/Wakfu_complete_pipeline/blob/019d2571e552b345a7d85a15901f043b46c30d57/1_Log_reader/src/classes/LogParser.py), [état et projection](https://github.com/Tochimizu/Wakfu_complete_pipeline/blob/019d2571e552b345a7d85a15901f043b46c30d57/1_Log_reader/src/classes/GameState.py), [API](https://github.com/Tochimizu/Wakfu_complete_pipeline/blob/019d2571e552b345a7d85a15901f043b46c30d57/1_Log_reader/src/main.py).
- [Détecteur](https://github.com/Tochimizu/Wakfu_complete_pipeline/blob/019d2571e552b345a7d85a15901f043b46c30d57/yolo-opencv-detector/vision/detector.py) et [notebook d’entraînement](https://github.com/Tochimizu/Wakfu_complete_pipeline/blob/019d2571e552b345a7d85a15901f043b46c30d57/yolo-opencv-detector/3_yolo_model_training.ipynb).

- Microsoft — Réseau WSL : https://learn.microsoft.com/windows/wsl/networking
- Docker — Backend WSL 2 : https://docs.docker.com/desktop/features/wsl/
- Docker — Accès GPU avec Compose : https://docs.docker.com/compose/how-tos/gpu-support/

Les choix de découpage, de protocole et de gestion des cycles décrits ici sont des propositions d’architecture pour ce projet. Les références documentent les possibilités de l’environnement ; elles ne valident pas encore les performances du système envisagé.
