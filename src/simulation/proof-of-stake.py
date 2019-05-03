'''
Simulate proof of stakes 
'''
from component import UserNode
import random

def main():
    '''
    Simulate proof of stakes with n users
    '''
    n = 10
    users = [None] * n #List of users
    prob = [None] * n
    stakes = [None] * n
    total_stakes = 0
    for i in range(n):
        users[i] = UserNode(i)
        storage = random.randint(1, 100000)
        users[i].add_storage(storage)
        total_stakes += users[i].fake_stake()
    
    for i in range(n):
        stakes[i] = users[i].fake_stake()
        prob[i] = users[i].fake_stake()/total_stakes

    for i in range(1, n):
        prob[i] += prob[i-1]
    
    print(stakes)
    print(prob)

    # Choosing next stake randomly by 
    select = random.random()
    for i in range(n):
        if select < prob[i]:
            print(i)
            return
    return

if __name__ == "__main__":
    main()