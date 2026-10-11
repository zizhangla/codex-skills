import com.comsol.model.*;
import com.comsol.model.util.*;

public class ComsolSmoke {
  public static Model run() throws Exception {
    Model m=ModelUtil.create("ComsolSmoke");
    m.component().create("comp1",true);
    m.component("comp1").geom().create("geom1",2);
    m.component("comp1").geom("geom1").create("sq1","Square");
    m.component("comp1").geom("geom1").feature("sq1").set("size",1);
    m.component("comp1").geom("geom1").run();
    m.component("comp1").physics().create("c","CoefficientFormPDE","geom1");
    m.component("comp1").physics("c").feature("cfeq1").set("c",1);
    m.component("comp1").physics("c").feature("cfeq1").set("a",0);
    m.component("comp1").physics("c").feature("cfeq1").set("f",0);
    m.component("comp1").physics("c").create("dir1","DirichletBoundary",1);
    m.component("comp1").physics("c").feature("dir1").selection().all();
    m.component("comp1").physics("c").feature("dir1").set("r","x/1[m]");
    m.component("comp1").mesh().create("mesh1");
    m.component("comp1").mesh("mesh1").autoMeshSize(5);
    m.component("comp1").mesh("mesh1").run();
    m.study().create("std1");
    m.study("std1").create("stat","Stationary");
    m.study("std1").run();
    m.result().numerical().create("int1","IntSurface");
    m.result().numerical("int1").selection().all();
    m.result().numerical("int1").set("expr",new String[]{"u","1","(u-x/1[m])^2"});
    double[][] v=m.result().numerical("int1").getReal();
    if(v.length!=3 || v[0].length!=1 || v[1].length!=1 || v[2].length!=1)
      throw new IllegalStateException("unexpected result shape");
    System.out.println("COMSOL_SMOKE_RESULT={\"integral_u\":"+v[0][0]+",\"area\":"+v[1][0]+",\"squared_error_integral\":"+v[2][0]+"}");
    System.out.println("COMSOL_SMOKE_DONE");
    return m;
  }
  public static void main(String[] args) throws Exception { run(); }
}
