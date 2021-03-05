import math

class Vector:

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
    
    def __add__(self, other):
        if isinstance(other, self.__class__):
            return Vector(self.x + other.x, self.y + other.y)
        return Vector(self.x + other, self.y + other)
    
    def __mul__(self, other):
        if isinstance(other, self.__class__):
            return Vector(self.x * other.x, self.y * other.y)
        return Vector(self.x * other, self.y * other)

    def __truediv__(self, other):
        if isinstance(other, self.__class__):
            return Vector(self.x / other.x, self.y / other.y)
        return Vector(self.x / other, self.y / other)

    def __sub__(self, other):
        if isinstance(other, self.__class__):
            return Vector(self.x - other.x, self.y - other.y)
        return Vector(self.x - other, self.y - other)
    
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.x == other.x and self.y == other.y
        return self.x == other and self.y == other
    
    def length(self):
        """calculates the length of the Vector

        Returns:
            [float]: square root of the vector squared
        """
        return math.sqrt(self.x*self.x + self.y*self.y)
    
    def length_sqr(self):
        return self.x*self.x + self.y*self.y
    
    def normalized(self):
        return self / self.length()

def length_sqr(vec):
    return vec.x ** 2 + vec.y ** 2

def dist_sqr(vec1, vec2):
    return length_sqr(vec1 - vec2)

def dot_product(a: Vector, b:Vector):
    """takes in nomralized Vectors and finds the dot product vector
    1 if facing same way, -1 if in opposite directions and 0 if in other direction

    Args:
        a (Vector): vector 1
        b (Vector): vector 2

    Returns:
        [float]: the dot calculation of the two vectors
    """
    return a.x * b.x + a.y * b.y

def approach(goal, current, dt):
    difference = goal - current
    if difference > dt:
        return current + dt
    if difference < -dt:
        return current - dt
    return goal
