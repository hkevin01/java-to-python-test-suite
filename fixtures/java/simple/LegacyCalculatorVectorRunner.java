import java.nio.file.Files;
import java.nio.file.Path;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class LegacyCalculatorVectorRunner {
    private static final Pattern VECTOR_PATTERN = Pattern.compile(
        "\\{\\s*\"id\"\\s*:\\s*\"([^\"]+)\"\\s*,\\s*\"input\"\\s*:\\s*\\{\\s*\"base\"\\s*:\\s*(-?\\d+)\\s*,\\s*\"multiplier\"\\s*:\\s*(-?\\d+)\\s*,\\s*\"premium\"\\s*:\\s*(true|false)\\s*\\}\\s*,\\s*\"expected\"\\s*:\\s*(-?\\d+)\\s*\\}",
        Pattern.DOTALL
    );

    public static void main(String[] args) throws Exception {
        if (args.length != 1) {
            System.err.println("Usage: java LegacyCalculatorVectorRunner <vectors.json>");
            System.exit(1);
        }

        String content = Files.readString(Path.of(args[0]));
        Matcher matcher = VECTOR_PATTERN.matcher(content);

        while (matcher.find()) {
            String id = matcher.group(1);
            int base = Integer.parseInt(matcher.group(2));
            int multiplier = Integer.parseInt(matcher.group(3));
            boolean premium = Boolean.parseBoolean(matcher.group(4));
            int expected = Integer.parseInt(matcher.group(5));
            int actual = LegacyCalculator.calculateScore(base, multiplier, premium);

            // Output format: id,actual,expected
            System.out.println(id + "," + actual + "," + expected);
        }
    }
}