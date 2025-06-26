import pygame
import sys
import os
import config
import time
import datetime
import numpy as np
import cv2
import logging
import shutil
import random
import odoorpc

class Tableau:
    def __init__(self):
        screen_info = pygame.display.Info()
        self.screen_width = screen_info.current_w
        self.screen_height = screen_info.current_h

        # background image
        self.background_image = pygame.transform.scale(pygame.image.load(config.manuscrit['path']),
                                                    (self.screen_width, self.screen_height))
        self.anime_page = []
        self.anime_page_state = 'wait'
        for path in config.anime_page:
            self.anime_page.append(pygame.transform.scale(pygame.image.load(path),
                                    (self.screen_width, self.screen_height)))
        # configuration
        self.load_config_page()
        self.input_image = config.input_image
        self.dessins = []
        self.odoo = self.connect_odoo()
        self.tableau_id = 0

    def connect_odoo(self):
        """ connect to odoo """
        server = config.odoo['host']
        db_name = config.odoo['db_name']
        user = config.odoo['user']
        password = config.odoo['password']
        odoo = odoorpc.ODOO(server, port=8069)
        odoo.login(db_name, user, password)
        return odoo

    def load_config_page(self):
        """ convert x, y page to real full screen  (x, y, largeur, hauteur)"""
        ratio_x =  self.screen_width / config.manuscrit['image'][2]
        ratio_y = self.screen_height / config.manuscrit['image'][3]
        page1 = config.manuscrit['page1']
        page2 = config.manuscrit['page2']
        self.page1 = pygame.Rect(page1[0] * ratio_x, page1[1] * ratio_y, page1[2] * ratio_x,  page1[3] * ratio_y)
        self.page2 = pygame.Rect(page2[0] * ratio_x, page2[1] * ratio_y, page2[2] * ratio_x,  page2[3] * ratio_y)

    def list_dessin_path(self):
        """ return the list of dessin already loaded """
        res = []
        for dessin in self.dessins:
            if dessin.path_image not in res:
                res.append(dessin.path_image)
        return res

    def get_next_image(self):
        """ get a new image to show """
        tableau = self.odoo.env['cartoon.tableau']

        try:
            result = tableau.get_next_image(tableau_id=self.tableau_id)
        except:
            result = {}
        print('-----get_next_image------', result)

        self.tableau_id = result.get('tableau_id', 0)

        if result.get('path_image'):
            dessin = Dessin()
            dessin.tableau_id = result.get('tableau_id', 0)
            dessin.path_image = result.get('path_image')
            #dessin.put_transpary()
            dessin.image = pygame.image.load(dessin.path_image)
            dessin.rect = dessin.image.get_rect()
            dessin.status = 'loaded'
            self.dessins.append(dessin)

    def ajuster_image(self, image, rect, ratio_h=1):
        image_largeur, image_hauteur = image.get_size()

        # Calcul du rapport d'aspect de l'image et du rectangle
        rapport_image = image_largeur / image_hauteur
        rapport_rectangle = rect.width / (rect.height / ratio_h)

        # Redimensionner l'image selon le rapport d'aspect
        if rapport_image > rapport_rectangle:
            # L'image est plus large, ajuster selon la largeur
            nouvelle_largeur = rect.width
            nouvelle_hauteur = int(nouvelle_largeur / rapport_image)
        else:
            # L'image est plus haute, ajuster selon la hauteur
            nouvelle_hauteur = (rect.height / ratio_h)
            nouvelle_largeur = int(nouvelle_hauteur * rapport_image)

        return pygame.transform.scale(image, (nouvelle_largeur, nouvelle_hauteur))


class Dessin(pygame.sprite.Sprite):
    """ Picture of arras book """
    def __init__(self):
        super().__init__()
        self.status = 'draft'
        self.tableau_id = 0
        self.time = time.time()
        self.path_image = ''
        self.image = False
        self.transparency = False
        self.page = ''
        self.position = '0-0-0'
        self.topleft = (0, 0)

    def put_transpary(self):
        # Charger l'image avec OpenCV en mode couleur (et alpha si existant)
        if self.path_image and not self.transparency:
            image = cv2.imread(self.path_image, cv2.IMREAD_UNCHANGED)

            if image.shape[2] == 4:  # Si l'image possède un canal alpha
                # Séparer les canaux BGR et Alpha
                bgr = image[:, :, :3]
                alpha_original = image[:, :, 3]  # Extraire le canal alpha existant
                # Convertir BGR en niveaux de gris
                grayscale = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

                # Additionner les valeurs du canal de gris avec le canal alpha existant
                alpha = np.minimum(alpha_original, 255 - grayscale)
                #alpha = np.clip(alpha, 0, 255)
                # Créer une nouvelle image RGBA en combinant les niveaux de gris avec le canal alpha
            else:
                # Si l'image est en RGB (sans alpha)
                grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                alpha = 255 - grayscale.copy()  # Le canal alpha est basé sur les niveaux de gris

            #rgba = cv2.merge([grayscale, grayscale, grayscale, alpha])
            rgba = cv2.merge([grayscale, grayscale, grayscale, alpha])

            # Enregistrer l'image en PNG (avec transparence)
            cv2.imwrite(self.path_image, rgba)
            self.transparency = True
            self.status = 'ready'


# Initialisation de Pygame
pygame.init()
premier_tableau = Tableau()
screen = pygame.display.set_mode((premier_tableau.screen_width, premier_tableau.screen_height), pygame.FULLSCREEN)

# Initialiser l'horloge pour contrôler la fréquence
clock = pygame.time.Clock()
fps = 2



# Boucle d'événements pour garder l'image à l'écran
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            running = False

    # Afficher le background
    screen.fill((0, 0, 0)) 
    screen.blit(premier_tableau.background_image, (0, 0))
    # afficher les dessins



    premier_tableau.get_next_image()
    print('---------------', premier_tableau.tableau_id, len(premier_tableau.dessins))


    if premier_tableau.anime_page_state == 'wait':


        if premier_tableau.tableau_id != 0 and premier_tableau.dessins:
            dessin = premier_tableau.dessins[-1]
            print('-----dessin--0-----', premier_tableau.dessins[0].path_image)
            print('-----dessin--1-----', premier_tableau.dessins[-1].path_image)
            page = premier_tableau.page2
            image_redimensionnee = premier_tableau.ajuster_image(dessin.image, page)
            image_rec = image_redimensionnee.get_rect()
            adjust_y = page.topleft[0]
            topleft = page.topleft

            if premier_tableau.page2.height > image_rec.height:
                topleft = (adjust_y, int((premier_tableau.page2.height - image_rec.height) / 2))
            else:
                topleft = premier_tableau.page2.topleft
            screen.blit(image_redimensionnee, topleft)
            dessin.topleft = topleft
            dessin.image = image_redimensionnee
            dessin.rect = dessin.image.get_rect()

        elif premier_tableau.tableau_id != 0:
            pass

        else:
            premier_tableau.anime_page_state = 'start'
            premier_tableau.dessins = []
    else:

        if premier_tableau.anime_page_state == 'start':
            premier_tableau.anime_page_state = '0'
        elif premier_tableau.anime_page_state.isdigit():
            anime_i = int(premier_tableau.anime_page_state)
            if len(premier_tableau.anime_page) > anime_i:
                screen.blit(premier_tableau.anime_page[anime_i], (0, 0))
                premier_tableau.anime_page_state = str(anime_i + 1)
            else:
                # End of anime
                premier_tableau.anime_page_state = 'wait'
                screen.blit(premier_tableau.background_image, (0, 0))

    pygame.display.flip()
    clock.tick(fps)


# Quitter Pygame
pygame.quit()
sys.exit()
