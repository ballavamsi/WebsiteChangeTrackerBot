from botframework.bot import Bot


def main():
    try:
        b = Bot()
    except Exception as e:
        print(e)
        print("Restarting bot...")
        main()


if __name__ == "__main__":
    main()
