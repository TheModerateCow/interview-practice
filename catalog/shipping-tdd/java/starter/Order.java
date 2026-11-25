import java.util.List;

public record Order(List<Parcel> parcels, int zone, int subtotalCents, boolean express, String promoCode) {}
