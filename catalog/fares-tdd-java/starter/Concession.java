/** Fare type of a travel card: share of the fare paid, daily cap, weekly cap (cents). */
public enum Concession {
    ADULT(100, 1200, 4800),
    CHILD(50, 600, 2400),
    SENIOR(70, 840, 3360);

    final int payPercent;
    final int dailyCap;
    final int weeklyCap;

    Concession(int payPercent, int dailyCap, int weeklyCap) {
        this.payPercent = payPercent;
        this.dailyCap = dailyCap;
        this.weeklyCap = weeklyCap;
    }
}
