Refactoring Types: ['Move Method', 'Extract Method']
rning4j/optimize/solvers/BackTrackLineSearch.java
/*
 *
 *  * Copyright 2015 Skymind,Inc.
 *  *
 *  *    Licensed under the Apache License, Version 2.0 (the "License");
 *  *    you may not use this file except in compliance with the License.
 *  *    You may obtain a copy of the License at
 *  *
 *  *        http://www.apache.org/licenses/LICENSE-2.0
 *  *
 *  *    Unless required by applicable law or agreed to in writing, software
 *  *    distributed under the License is distributed on an "AS IS" BASIS,
 *  *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  *    See the License for the specific language governing permissions and
 *  *    limitations under the License.
 *
 */

package org.deeplearning4j.optimize.solvers;

import org.apache.commons.math3.util.FastMath;
import static org.nd4j.linalg.ops.transforms.Transforms.*;

import org.deeplearning4j.exception.InvalidStepException;
import org.deeplearning4j.nn.api.Model;
import org.deeplearning4j.optimize.api.ConvexOptimizer;
import org.deeplearning4j.optimize.api.StepFunction;
import org.deeplearning4j.optimize.stepfunctions.DefaultStepFunction;
import org.nd4j.linalg.api.ndarray.INDArray;
import org.nd4j.linalg.api.ops.impl.scalar.comparison.ScalarSetValue;
import org.nd4j.linalg.api.ops.impl.transforms.comparison.Eps;
import org.nd4j.linalg.factory.Nd4j;
import org.deeplearning4j.optimize.api.LineOptimizer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;


//"Line Searches and Backtracking", p385, "Numeric Recipes in C"
/**
 @author Aron Culotta <a href="mailto:culotta@cs.umass.edu">culotta@cs.umass.edu</a>

 Adapted from mallet with original authors above.
 Modified to be a vectorized version that uses jblas matrices
 for computation rather than the mallet ops.


 Numerical Recipes in C: p.385. lnsrch. A simple backtracking line
 search. No attempt at accurately finding the true minimum is
 made. The goal is only to ensure that BackTrackLineSearch will
 return a position of higher value.

 @author Adam Gibson


 */

public class BackTrackLineSearch implements LineOptimizer  {
    private static final Logger logger = LoggerFactory.getLogger(BackTrackLineSearch.class.getName());

    private Model function;
    private StepFunction stepFunction = new DefaultStepFunction();
    private ConvexOptimizer optimizer;
    private int maxIterations = 5;
    double stpmax = 100;

    // termination conditions: either
    //   a) abs(delta x/x) < REL_TOLX for all coordinates
    //   b) abs(delta x) < ABS_TOLX for all coordinates
    //   c) sufficient function increase (uses ALF)
    private double relTolx = 1e-10f;
    private double absTolx = 1e-4f; // tolerance on absolute value difference
    final double ALF = 1e-4f;

    /**
     *
     * @param function
     * @param stepFunction
     * @param optimizer
     */
    public BackTrackLineSearch(Model function, StepFunction stepFunction, ConvexOptimizer optimizer) {
        this.function = function;
        this.stepFunction = stepFunction;
        this.optimizer = optimizer;
    }

    /**
     *
     * @param optimizable
     * @param optimizer
     */
    public BackTrackLineSearch(Model optimizable, ConvexOptimizer optimizer) {
        this(optimizable, new DefaultStepFunction(),optimizer);
    }


    public void setStpmax(double stpmax) {
        this.stpmax = stpmax;
    }


    public double getStpmax() {
        return stpmax;
    }

    /**
     * Sets the tolerance of relative diff in function value.
     *  Line search converges if abs(delta x / x) < tolx
     *  for all coordinates. */
    public void setRelTolx (double tolx) { relTolx = tolx; }

    /**
     * Sets the tolerance of absolute diff in function value.
     *  Line search converges if abs(delta x) < tolx
     *  for all coordinates. */
    public void setAbsTolx (double tolx) { absTolx = tolx; }

    public int getMaxIterations() {
        return maxIterations;
    }

    public void setMaxIterations(int maxIterations) {
        this.maxIterations = maxIterations;
    }

    // initialStep is ignored.  This is b/c if the initial step is not 1.0,
    //   it sometimes confuses the backtracking for reasons I don't
    //   understand.  (That is, the jump gets LARGER on iteration 1.)

    // returns fraction of step size (alam) if found a good step
    // returns 0.0 if could not step in direction

    /**
     *
     * @param initialStep the initial step size
     * @param parameters the parameters to optimize
     * @param gradients the line/rate of change
     * @return the next step size
     * @throws InvalidStepException
     */
    public double optimize (double initialStep,INDArray parameters,INDArray gradients) throws InvalidStepException {
        double slope, test, alamin, alam, alam2, tmplam;
        double rhs1, rhs2, a, b, disc, oldAlam;double f, fold, f2;
        INDArray oldParameters = parameters.dup();
        INDArray gDup = gradients.dup();

        alam2 = 0.0;
        f2 = fold = optimizer.score();

        if (logger.isDebugEnabled()) {
            logger.trace ("ENTERING BACKTRACK\n");
            logger.trace("Entering BackTrackLinnSearch, value = " + fold + ",\ndirection.oneNorm:"
                    +	gDup.norm1(Integer.MAX_VALUE) + "  direction.infNorm:"+ FastMath.max(Float.NEGATIVE_INFINITY,abs(gDup).max(Integer.MAX_VALUE).getDouble(0)));
        }

        double sum = gradients.norm2(Integer.MAX_VALUE).getDouble(0);
        if(sum > stpmax) {
            logger.warn("attempted step too big. scaling: sum= " + sum +
                    ", stpmax= "+ stpmax);
            gradients.muli(stpmax / sum);
        }

        //dot product
        slope = Nd4j.getBlasWrapper().dot(gDup, gradients);
        logger.debug("slope = " + slope);

        if (slope < 0)
            throw new InvalidStepException("Slope = " + slope + " is negative");

        if (slope == 0)
            throw new InvalidStepException ("Slope = " + slope + " is zero");

        // find maximum lambda
        // converge when (delta x) / x < REL_TOLX for all coordinates.
        //  the largest step size that triggers this threshold is
        //  precomputed and saved in alamin
        INDArray maxOldParams = abs(oldParameters);
        Nd4j.getExecutioner().exec(new ScalarSetValue(maxOldParams,1));



        INDArray testMatrix = abs(gradients).divi(maxOldParams);
        test = testMatrix.max(Integer.MAX_VALUE).getDouble(0);

        alamin = relTolx / test;

        alam  = 1.0;
        oldAlam = 0.0;
        int iteration;
        // look for step size in direction given by "line"
        for(iteration = 0; iteration < maxIterations; iteration++) {
            // initially, alam = 1.0, i.e. take full Newton step
            logger.trace("BackTrack loop iteration " + iteration +" : alam=" + alam +" oldAlam=" + oldAlam);
            logger.trace ("before step, x.1norm: " + parameters.norm1(Integer.MAX_VALUE) +  "\nalam: " + alam + "\noldAlam: " + oldAlam);
            assert(alam != oldAlam) : "alam == oldAlam";

            if(stepFunction == null)
                stepFunction =  new DefaultStepFunction();
            //scale wrt updates
            stepFunction.step(parameters, gradients, new Object[]{alam,oldAlam}); //step

            if(logger.isDebugEnabled())  {
                double norm1 = parameters.norm1(Integer.MAX_VALUE).getDouble(0);
                logger.debug ("after step, x.1norm: " + norm1);
            }

            // check for convergence
            //convergence on delta x
            //if all of the parameters are < 1e-12

            if ((alam < alamin) || Nd4j.getExecutioner().execAndReturn(new Eps(oldParameters, parameters,
                    parameters.dup(), parameters.length())).sum(Integer.MAX_VALUE).getDouble(0) == parameters.length()) {
                function.setParams(oldParameters);
                function.setScore();
                f = function.score();
                logger.trace("EXITING BACKTRACK: Jump too small (alamin = "+ alamin + "). Exiting and using xold. Value = " + f);
                return 0.0;
            }

            function.setParams(parameters);
            oldAlam = alam;
            function.setScore();
            f = function.score();

            logger.debug("value = " + f);

            // sufficient function increase (Wolf condition)
            if(f >= fold + ALF * alam * slope) {

                logger.debug("EXITING BACKTRACK: value=" + f);

                if (f < fold)
                    throw new IllegalStateException
                            ("Function did not increase: f = " + f + " < " + fold + " = fold");
                return alam;
            }


            // if value is infinite, i.e. we've
            // jumped to unstable territory, then scale down jump
            else if(Double.isInfinite(f) || Double.isInfinite(f2)) {
                logger.warn ("Value is infinite after jump " + oldAlam + ". f="+ f +", f2=" + f2 + ". Scaling back step size...");
                tmplam = .2 * alam;
                if(alam < alamin) { //convergence on delta x
                    function.setParams(oldParameters);
                    function.setScore();
                    f = function.score();
                    logger.warn("EXITING BACKTRACK: Jump too small. Exiting and using xold. Value="+ f );
                    return 0.0;
                }
            }
            else { // backtrack
                if(alam == 1.0) // first time through
                    tmplam = -slope / (2.0 * ( f - fold - slope ));
                else {
                    rhs1 = f - fold- alam * slope;
                    rhs2 = f2 - fold - alam2 * slope;
                    if((alam - alam2) == 0)
                        throw new IllegalStateException("FAILURE: dividing by alam-alam2. alam=" + alam);
                    a = ( rhs1 / (FastMath.pow(alam, 2)) - rhs2 /  ( FastMath.pow(alam2, 2) )) / (alam - alam2);
                    b = ( -alam2 * rhs1/( alam* alam ) + alam * rhs2 / ( alam2 *  alam2 )) / ( alam - alam2);
                    if(a == 0.0)
                        tmplam = -slope / (2.0 * b);
                    else {
                        disc = b * b - 3.0 * a * slope;
                        if(disc < 0.0) {
                            tmplam = .5f * alam;
                        }
                        else if (b <= 0.0)
                            tmplam = (-b + FastMath.sqrt(disc))/(3.0f * a );
                        else
                            tmplam = -slope / (b +FastMath.sqrt(disc));
                    }
                    if (tmplam > .5f * alam)
                        tmplam = .5f * alam;    // lambda <= .5 lambda_1
                }
            }

            alam2 = alam;
            f2 = f;
            logger.debug("tmplam:" + tmplam);
            alam = Math.max(tmplam, .1f * alam);  // lambda >= .1*Lambda_1

        }

        return 0.0;
    }




}



File: deeplearning4j-core/src/test/java/org/deeplearning4j/optimize/solver/BackTrackLineSearchTest.java
package org.deeplearning4j.optimize.solver;

import org.deeplearning4j.datasets.iterator.impl.IrisDataSetIterator;
import org.deeplearning4j.nn.api.OptimizationAlgorithm;
import org.deeplearning4j.nn.conf.NeuralNetConfiguration;
import org.deeplearning4j.nn.layers.OutputLayer;
import org.deeplearning4j.nn.layers.factory.LayerFactories;
import org.deeplearning4j.nn.weights.WeightInit;
import org.deeplearning4j.optimize.api.IterationListener;
import org.deeplearning4j.optimize.listeners.ScoreIterationListener;
import org.deeplearning4j.optimize.solvers.BackTrackLineSearch;
import org.junit.Test;
import org.nd4j.linalg.dataset.DataSet;
import org.nd4j.linalg.lossfunctions.LossFunctions;

import java.util.Arrays;

import static org.junit.Assert.*;

/**
 * @author Adam Gibson
 */
public class BackTrackLineSearchTest {
    @Test
    public void testLineSearch() throws Exception {
        NeuralNetConfiguration conf = new NeuralNetConfiguration.Builder()
                .lossFunction(LossFunctions.LossFunction.MCXENT).optimizationAlgo(OptimizationAlgorithm.ITERATION_GRADIENT_DESCENT)
                .activationFunction("softmax")
                .iterations(10).weightInit(WeightInit.XAVIER)
                .learningRate(1e-1).nIn(4).nOut(3).layer(new org.deeplearning4j.nn.conf.layers.OutputLayer()).build();

        OutputLayer l = LayerFactories.getFactory(conf.getLayer()).create(conf, Arrays.<IterationListener>asList(new ScoreIterationListener(1)),0);
        DataSet d = new IrisDataSetIterator(1,1).next();
        d.normalizeZeroMeanZeroUnitVariance();
        l.setInput(d.getFeatureMatrix());
        l.setLabels(d.getLabels());
        BackTrackLineSearch lineSearch = new BackTrackLineSearch(l,l.getOptimizer());
        double step = lineSearch.optimize(1.0,l.params(),l.gradient().gradient());
        assertEquals(0.0,step,1e-1);
    }

}


File: deeplearning4j-core/src/test/java/org/deeplearning4j/plot/ListenerTest.java
package org.deeplearning4j.plot;

import org.deeplearning4j.base.MnistFetcher;
import org.deeplearning4j.datasets.fetchers.IrisDataFetcher;
import org.deeplearning4j.datasets.fetchers.MnistDataFetcher;
import org.deeplearning4j.datasets.iterator.DataSetIterator;
import org.deeplearning4j.datasets.iterator.impl.IrisDataSetIterator;
import org.deeplearning4j.datasets.iterator.impl.MnistDataSetIterator;
import org.deeplearning4j.nn.api.OptimizationAlgorithm;
import org.deeplearning4j.nn.conf.MultiLayerConfiguration;
import org.deeplearning4j.nn.conf.NeuralNetConfiguration;
import org.deeplearning4j.nn.conf.distribution.NormalDistribution;
import org.deeplearning4j.nn.conf.distribution.UniformDistribution;
import org.deeplearning4j.nn.conf.layers.OutputLayer;
import org.deeplearning4j.nn.conf.layers.RBM;
import org.deeplearning4j.nn.conf.override.ClassifierOverride;
import org.deeplearning4j.nn.conf.override.ConfOverride;
import org.deeplearning4j.nn.multilayer.MultiLayerNetwork;
import org.deeplearning4j.nn.weights.WeightInit;
import org.deeplearning4j.optimize.api.IterationListener;
import org.deeplearning4j.plot.iterationlistener.*;
import org.junit.Test;
import org.nd4j.linalg.dataset.DataSet;
import org.nd4j.linalg.dataset.api.iterator.fetcher.DataSetFetcher;
import org.nd4j.linalg.factory.Nd4j;
import org.nd4j.linalg.lossfunctions.LossFunctions;
import static org.junit.Assert.*;

import java.io.IOException;
import java.util.Arrays;
import java.util.Collections;


public class ListenerTest {

    /** Very simple back-prop config set up for Iris.
     * Learning Rate = 0.1
     * No regularization, no Adagrad, no momentum etc. One iteration.
     */

    private DataSetIterator irisIter = new IrisDataSetIterator(50,50);


    @Test
    public void testNeuralNetGraphsCapturedMLPNetwork() {
        MultiLayerNetwork network = new MultiLayerNetwork(getIrisMLPSimpleConfig(new int[]{5}, "sigmoid"));
        network.init();
        DataSet data = irisIter.next();
        IterationListener listener = new NeuralNetPlotterIterationListener(1,true);

        network.setListeners(Collections.singletonList(listener));
        network.fit(data.getFeatureMatrix(), data.getLabels());
        assertNotNull(network.getListeners().get(0));
        assertEquals(listener.invoked(), true);
    }


    @Test
    public void testAccuracyGraphCaptured() {
        MultiLayerNetwork network = new MultiLayerNetwork(getIrisSimpleConfig(new int[]{10}, "sigmoid", 10));
        network.init();
        DataSet data = irisIter.next();
        IterationListener listener = new AccuracyPlotterIterationListener(1, network, data);

        network.setListeners(Collections.singletonList(listener));
        network.fit(data.getFeatureMatrix(), data.getLabels());
        assertNotNull(network.getListeners().get(0).toString());
        assertEquals(listener.invoked(), true);
    }

    @Test
    public void testMultipleGraphsCapturedForMultipleLayers() {
        // Tests Gradient Plotter and Loss Plotter
        MultiLayerNetwork network = new MultiLayerNetwork(getIrisSimpleConfig(new int[]{10, 5}, "sigmoid", 5));
        network.init();
        IterationListener listener = new GradientPlotterIterationListener(4);
        IterationListener listener2 = new LossPlotterIterationListener(4);
        network.setListeners(Arrays.asList(listener, listener2));
        while( irisIter.hasNext() ) network.fit(irisIter.next());
        assertNotNull(network.getListeners().get(1).toString());
        assertEquals(listener2.invoked(), true);
    }

    private static MultiLayerConfiguration getIrisSimpleConfig( int[] hiddenLayerSizes, String activationFunction, int iterations ) {
        MultiLayerConfiguration c = new NeuralNetConfiguration.Builder()
                .nIn(4).nOut(3)
                .weightInit(WeightInit.DISTRIBUTION)
                .dist(new NormalDistribution(0, 0.1))

                .activationFunction(activationFunction)
                .lossFunction(LossFunctions.LossFunction.RMSE_XENT)
                .optimizationAlgo(OptimizationAlgorithm.GRADIENT_DESCENT)

                .iterations(iterations)
                .batchSize(1)
                .constrainGradientToUnitNorm(false)
                .corruptionLevel(0.0)

                .layer(new RBM())
                .learningRate(0.1).useAdaGrad(false)

                .regularization(false)
                .l1(0.0)
                .l2(0.0)
                .dropOut(0.0)
                .momentum(0.0)
                .applySparsity(false).sparsity(0.0)
                .seed(12345L)

                .list(hiddenLayerSizes.length + 1).hiddenLayerSizes(hiddenLayerSizes)
                .useDropConnect(false)

                .override(hiddenLayerSizes.length, new ConfOverride() {
                    @Override
                    public void overrideLayer(int i, NeuralNetConfiguration.Builder builder) {
                        builder.activationFunction("softmax");
                        builder.layer(new OutputLayer());
                        builder.weightInit(WeightInit.DISTRIBUTION);
                        builder.dist(new NormalDistribution(0, 0.1));
                    }
                }).build();


        return c;
    }

    private static MultiLayerConfiguration getIrisMLPSimpleConfig( int[] hiddenLayerSizes, String activationFunction ) {
        MultiLayerConfiguration c = new NeuralNetConfiguration.Builder()
                .nIn(4).nOut(3)
                .weightInit(WeightInit.DISTRIBUTION)
                .dist(new NormalDistribution(0, 0.1))

                .activationFunction(activationFunction)
                .lossFunction(LossFunctions.LossFunction.RMSE_XENT)
                .optimizationAlgo(OptimizationAlgorithm.GRADIENT_DESCENT)

                .iterations(1)
                .batchSize(1)
                .constrainGradientToUnitNorm(false)
                .corruptionLevel(0.0)

                .layer(new RBM())
                .learningRate(0.1).useAdaGrad(false)

                .regularization(false)
                .l1(0.0)
                .l2(0.0)
                .dropOut(0.0)
                .momentum(0.0)
                .applySparsity(false).sparsity(0.0)
                .seed(12345L)

                .list(hiddenLayerSizes.length + 1)
                .hiddenLayerSizes(hiddenLayerSizes)
                .backward(true).pretrain(false)
                .useDropConnect(false)

                .override(hiddenLayerSizes.length, new ConfOverride() {
                    @Override
                    public void overrideLayer(int i, NeuralNetConfiguration.Builder builder) {
                        builder.activationFunction("softmax");
                        builder.layer(new OutputLayer());
                        builder.weightInit(WeightInit.DISTRIBUTION);
                        builder.dist(new NormalDistribution(0, 0.1));
                    }
                }).build();


        return c;
    }


    @Test
    public void testBackTrackLine() {
        Nd4j.MAX_SLICES_TO_PRINT = -1;
        Nd4j.MAX_ELEMENTS_PER_SLICE = -1;

        DataSetIterator irisIter = new IrisDataSetIterator(1,1);
        DataSet data = irisIter.next();

        MultiLayerNetwork network = new MultiLayerNetwork(getIris1ItConfig(new int[]{5}, "sigmoid", 1));
        network.init();

        network.fit(data.getFeatureMatrix(), data.getLabels());
    }


    private static MultiLayerConfiguration getIris1ItConfig( int[] hiddenLayerSizes, String activationFunction, int iterations ) {
        MultiLayerConfiguration c = new NeuralNetConfiguration.Builder()
                .nIn(4).nOut(3)
                .weightInit(WeightInit.DISTRIBUTION)
                .dist(new NormalDistribution(0, 0.1))

                .activationFunction(activationFunction)
                .lossFunction(LossFunctions.LossFunction.RMSE_XENT)
                .optimizationAlgo(OptimizationAlgorithm.GRADIENT_DESCENT)

                .iterations(iterations)
                .batchSize(1)
                .constrainGradientToUnitNorm(false)
                .corruptionLevel(0.0)

                .layer(new RBM())
                .learningRate(0.1).useAdaGrad(false)
                .numLineSearchIterations(1)
                .regularization(false)
                .l1(0.0)
                .l2(0.0)
                .dropOut(0.0)
                .momentum(0.0)
                .applySparsity(false).sparsity(0.0)
                .seed(12345L)

                .list(hiddenLayerSizes.length + 1).hiddenLayerSizes(hiddenLayerSizes)
                .useDropConnect(false)

                .override(hiddenLayerSizes.length, new ConfOverride() {
                    @Override
                    public void overrideLayer(int i, NeuralNetConfiguration.Builder builder) {
                        builder.activationFunction("softmax");
                        builder.layer(new OutputLayer());
                        builder.weightInit(WeightInit.DISTRIBUTION);
                        builder.dist(new NormalDistribution(0, 0.1));
                    }
                }).build();


        return c;
    }


}
