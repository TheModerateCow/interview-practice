public class Shipping {
    static final int MAX_BILLABLE = 30000;
    static final int FREE_SHIPPING_MIN = 7500;
    static final int OVERSIZE_SIDE = 100;
    static final int OVERSIZE_FEE = 1500;
    static final int[] FIRST_KG = {0, 500, 650, 800, 1100};
    static final int[] PER_STEP = {0, 100, 140, 180, 250};

    // num/den rounded half up, for num >= 0.
    static int halfUp(int num, int den) { return (num + den / 2) / den; }

    public static int billableGrams(Parcel p) {
        if (p.weightGrams() <= 0 || p.lengthCm() <= 0 || p.widthCm() <= 0 || p.heightCm() <= 0)
            throw new InvalidParcelException("invalid parcel");
        int dim = (p.lengthCm() * p.widthCm() * p.heightCm() + 4) / 5;
        int g = Math.max(p.weightGrams(), dim);
        g = (g + 499) / 500 * 500;
        if (g > MAX_BILLABLE) throw new TooHeavyException("parcel too heavy");
        return g;
    }

    public static int quote(Order o) {
        if (o.parcels().isEmpty()) throw new NoParcelsException("order has no parcels");
        if (o.zone() < 1 || o.zone() > 4) throw new UnknownZoneException("unknown zone");
        String promo = o.promoCode();
        if (!promo.isEmpty() && !promo.equals("SHIP10") && !promo.equals("FLAT600"))
            throw new UnknownPromoException("unknown promo code");
        boolean free = o.subtotalCents() >= FREE_SHIPPING_MIN && o.zone() <= 3 && !o.express();
        int sum = 0;
        for (Parcel p : o.parcels()) {
            int g = billableGrams(p);
            int rate = FIRST_KG[o.zone()];
            if (g > 1000) rate += (g - 1000) / 500 * PER_STEP[o.zone()];
            if (o.express()) rate = halfUp(rate * 135, 100);
            if (free) rate = 0;
            if (Math.max(p.lengthCm(), Math.max(p.widthCm(), p.heightCm())) > OVERSIZE_SIDE) rate += OVERSIZE_FEE;
            sum += rate;
        }
        int total = sum + halfUp(sum * 85, 1000);
        if (promo.equals("SHIP10")) total -= total / 10;
        else if (promo.equals("FLAT600") && !free) total = Math.max(total - 600, 0);
        return total;
    }
}
