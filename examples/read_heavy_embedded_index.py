from certigap.api import CertiGapToolkit


def main() -> None:
    model = CertiGapToolkit().fit_distribution(
        kind="hot_tail",
        n=32,
        budget=6,
        eta=0.30,
        solver="beam",
    )
    print("Read-heavy embedded index")
    print(model.summary())
    cert = model.export_certificate()
    print("Certified gap:", cert["certified_gap"])


if __name__ == "__main__":
    main()
