
class ZoneDetection:
    def __init__(self):
        """ playing zone
        plot matix exemple
        [
        (200, 100)  # Haut-gauche
        (600, 100)  # Haut-droit
        (700, 400)  # Bas-droit
        (100, 400)  # Bas-gauche
        ]

        """
        self.pts_ground = []
        self.pts_image = []

        self.H = None #  homography matrix
        self.H_inv = None # inverse homography matrix

    def update_h(self):
        """ compute homography matrix """
        self.H = cv2.getPerspectiveTransform(self.pts_image, self.pts_ground)
        self.H_inv = np.linalg.inv(self.H)

    def image_to_ground(self, u, v):
        """ return x, y with homogrphy [(0,0), (100,100)] """
        if self.H is None:
            self.update_h()
        pt = np.array([[[u, v]]], dtype=np.float32)
        pt_transformed = cv2.perspectiveTransform(pt, self.H)
        return pt_transformed[0][0]

    def ground_to_image(self, X, Y):
        """
        Convertit une position au sol (X, Y) en mètres → en coordonnées image (u, v) en pixels
        """
        if self.H_inv is None:
            self.update_h()
        pt_ground = np.array([[[X, Y]]], dtype=np.float32)  # forme (1, 1, 2)
        pt_image = cv2.perspectiveTransform(pt_ground, self.H_inv)
        u, v = pt_image[0][0]
        return (int(u), int(v))

    def plot_in_image(self, plot):
        """ return true if the plot is in the zone
        plot = (x, y)
        """
        result = cv2.pointPolygonTest(self.pts_image, plot, False)
        if result >= 0:
            return True
        return False

    def plot_in_ground(self, plot):
        """ return true if the plot is in the zone
        plot = (x, y)
        """
        result = cv2.pointPolygonTest(self.pts_ground, plot, False)
        if result >= 0:
            return True
        return False

