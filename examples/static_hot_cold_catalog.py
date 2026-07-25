from certigap.api import CertiGapToolkit


def main() -> None:
    weights = [0.01] * 20
    for idx in range(8, 12):
        weights[idx] = 0.18
    model = CertiGapToolkit().fit(weights, budget=4, eta=0.10, solver="beam")
    print("Static hot/cold catalog")
    print(model.summary())
    print("Tree:", model.export_tree())


if __name__ == "__main__":
    main()
