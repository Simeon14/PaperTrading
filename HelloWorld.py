import random
answer = random.randint(1, 100)
print("Guess a number between 1 and 100")

while True:
    guess = int(input())

    if guess < answer:
        print("Too low! Try again.")
    elif guess > answer:
        print("Too high! Try again.")
    else:
        print("You guessed the number " + str(answer) + " correctly!")
        break