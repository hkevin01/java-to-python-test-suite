public class LegacyCalculator {
    public static int calculateScore(int base, int multiplier, boolean premium) {
        int score = base * multiplier;
        if (premium) {
            score += 25;
        }
        if (score > 100) {
            return 100;
        }
        if (score < 0) {
            return 0;
        }
        return score;
    }

    public static void main(String[] args) {
        int base = Integer.parseInt(args[0]);
        int multiplier = Integer.parseInt(args[1]);
        boolean premium = Boolean.parseBoolean(args[2]);
        System.out.println(calculateScore(base, multiplier, premium));
    }
}