import random


def main():
    answer = random.randint(1, 100)
    tries = 0

    print("1부터 100 사이의 숫자를 맞춰보세요!")

    while True:
        guess = input("숫자를 입력하세요: ")

        if not guess.isdigit():
            print("숫자만 입력해주세요.")
            continue

        guess = int(guess)
        tries += 1

        if guess < answer:
            print("낮습니다.")
        elif guess > answer:
            print("높습니다.")
        else:
            print(f"정답입니다! {tries}번만에 맞추셨습니다. 축하합니다!")
            break


if __name__ == "__main__":
    main()
