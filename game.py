''''Guess the number Game'''

import numpy as np
number = np.random.randint(1, 101) #guessed number
count = 0

while True:
    count += 1
    predict_number = int(input("Guess thr number from 1 to 100: "))
    
    if predict_number > number:
        print("The number has to be less")
        
    elif predict_number < number:
        print("The number has to be more")
    else:
        print(f"You guessed the number! This is {number}, it takes {count} times")
        break # end of game, go out from cycle