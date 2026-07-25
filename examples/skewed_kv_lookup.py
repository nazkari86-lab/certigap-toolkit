from certigap.api import CertiGapToolkit


def main() -> None:
    weights = [0.02, 0.02, 0.03, 0.04, 0.22, 0.24, 0.18, 0.10, 0.08, 0.07]
    model = CertiGapToolkit().fit(weights, budget=3, eta=0.15, solver="beam")
    print("Skewed key-value lookup")
    print(model.summary())
    print("Cost for hot key 6:", model.query_cost(6))
    print("Cost for cold key 1:", model.query_cost(1))
    print("Best baselines:", model.compare_baselines()[:4])


if __name__ == "__main__":
    main()
