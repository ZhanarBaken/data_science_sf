'''Guess the number Game
The machine predicts and guesses a number itself'''
import numpy as np

def random_predict(number:int=1) -> int:
    
    """Guess a number randomly

    Args:
        number (int, optional): Guessed number . Defaults to 1.

    Returns:
        int: Number of times
    """
    count = 0 
    
    while True:
        count += 1
        predict_number = np.random.randint(1, 101) #predicted the number
        if number == predict_number:
            break #the execution of the loop 
    return(count)

    
def score_game(random_predict) -> int:
    """How many in mean number of times from 1000 ways, our algorithm predict 

    Args:
        random_predict (_type_): func of predicting

    Returns:
        int: mean number of times 
    """
    count_ls = [] # the list for saving counting of guessess
    #np.random.seed(1) # record the seed for reproducibility
    random_array = np.random.randint(1, 101, size=(1000)) # guessed list of numbers
    
    for number in random_array:
        count_ls.append(random_predict(number))
        
    score = int(np.mean(count_ls))
    
    print(f'Your algorithm is guessing the number in mean for: {score} times')
    return(score)

# RUN
if __name__ == '__main__':
    score_game(random_predict)