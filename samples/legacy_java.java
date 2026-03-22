import java.util.*;
import java.io.*;
import java.text.SimpleDateFormat;

// Legacy Java 7 style — demo sample
public class StudentManager {

    private List<Map<String, Object>> students = new ArrayList<Map<String, Object>>();
    private String dataFile = "students.dat";

    public void loadStudents() throws IOException {
        BufferedReader br = null;
        try {
            br = new BufferedReader(new FileReader(dataFile));
            String line = null;
            while ((line = br.readLine()) != null) {
                String[] parts = line.split(",");
                Map<String, Object> student = new HashMap<String, Object>();
                student.put("id", Integer.parseInt(parts[0].trim()));
                student.put("name", parts[1].trim());
                student.put("grade", Double.parseDouble(parts[2].trim()));
                student.put("enrollDate", new SimpleDateFormat("yyyy-MM-dd").parse(parts[3].trim()));
                students.add(student);
            }
        } catch (Exception e) {
            System.out.println("Error loading students: " + e.getMessage());
        } finally {
            if (br != null) {
                try {
                    br.close();
                } catch (IOException e) {
                    e.printStackTrace();
                }
            }
        }
    }

    public List<Map<String, Object>> getTopStudents(int n) {
        List<Map<String, Object>> sorted = new ArrayList<Map<String, Object>>(students);
        for (int i = 0; i < sorted.size(); i++) {
            for (int j = i + 1; j < sorted.size(); j++) {
                double gi = (Double) sorted.get(i).get("grade");
                double gj = (Double) sorted.get(j).get("grade");
                if (gj > gi) {
                    Map<String, Object> tmp = sorted.get(i);
                    sorted.set(i, sorted.get(j));
                    sorted.set(j, tmp);
                }
            }
        }
        List<Map<String, Object>> result = new ArrayList<Map<String, Object>>();
        for (int i = 0; i < n && i < sorted.size(); i++) {
            result.add(sorted.get(i));
        }
        return result;
    }

    public double calculateAverage() {
        if (students == null || students.size() == 0) {
            return 0.0;
        }
        double sum = 0.0;
        for (Map<String, Object> s : students) {
            sum += (Double) s.get("grade");
        }
        return sum / students.size();
    }

    public Map<String, Object> findStudentById(int id) {
        for (Map<String, Object> s : students) {
            Integer sid = (Integer) s.get("id");
            if (sid != null && sid.equals(id)) {
                return s;
            }
        }
        return null;
    }

    public void printReport() {
        StringBuffer sb = new StringBuffer();
        sb.append("=== Student Report ===\n");
        sb.append("Total Students: " + students.size() + "\n");
        sb.append("Average Grade : " + String.format("%.2f", calculateAverage()) + "\n\n");
        for (Map<String, Object> s : students) {
            sb.append("ID:" + s.get("id") + " Name:" + s.get("name")
                    + " Grade:" + s.get("grade") + "\n");
        }
        System.out.println(sb.toString());
    }

    public static void main(String[] args) {
        StudentManager manager = new StudentManager();
        try {
            manager.loadStudents();
            manager.printReport();
            List<Map<String, Object>> top3 = manager.getTopStudents(3);
            System.out.println("Top 3 Students:");
            for (int i = 0; i < top3.size(); i++) {
                System.out.println((i + 1) + ". " + top3.get(i).get("name")
                        + " - " + top3.get(i).get("grade"));
            }
        } catch (IOException e) {
            System.out.println("Fatal error: " + e.getMessage());
            System.exit(1);
        }
    }
}
