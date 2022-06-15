import numpy as np

def optimal_predict(number: int = 1) -> int:
    '''The machine predicts and guesses a number less then 20 times

    Args:
        number (int, optional): Guessed number . Defaults to 1.

    Returns:
        int: Number of times
    '''
    
    min = 1
    max = 1000

    number = np.random.randint(min, max) #randomly guessed number 

    count = 0
    
# binary search
    while True:
        count+=1
        mid = (min+max) // 2
    
        if mid > number:
          max = mid
    
        elif mid < number:
          min = mid

        else:
            print(f"Компьютер угадал число за {count} попыток. Это число {number}")
            break #the execution of the loop 
    return count


def score_game(optimal_predict) -> int:

  """How many in mean number of times from 1000 ways, our algorithm predict 

    Args:
        optimal_predict (_type_): func of predicting

    Returns:
        int: mean number of times 
    """
  count_ls = []
  np.random.seed(1)  # record the seed for reproducibility
  random_array = np.random.randint(1, 101, size=(1000)) # guessed list of numbers
  
  for number in random_array:
    count_ls.append(optimal_predict(number))

  score = int(np.mean(count_ls))
  print(f"Ваш алгоритм угадывает число в среднем за: {score} попытки")
  
  
score_game(optimal_predict)

# RUN
if __name__ == '__main__':
    score_game(optimal_predict)