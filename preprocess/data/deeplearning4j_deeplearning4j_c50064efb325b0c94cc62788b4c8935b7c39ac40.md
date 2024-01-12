Refactoring Types: ['Extract Method']
ava/org/deeplearning4j/optimize/solvers/BaseOptimizer.java
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

import org.deeplearning4j.berkeley.Pair;
import org.deeplearning4j.exception.InvalidStepException;
import org.deeplearning4j.nn.api.Layer;
import org.deeplearning4j.nn.api.Model;
import org.deeplearning4j.nn.api.Updater;
import org.deeplearning4j.nn.conf.NeuralNetConfiguration;
import org.deeplearning4j.nn.gradient.DefaultGradient;
import org.deeplearning4j.nn.gradient.Gradient;
import org.deeplearning4j.nn.updater.UpdaterCreator;
import org.deeplearning4j.optimize.api.ConvexOptimizer;
import org.deeplearning4j.optimize.api.IterationListener;
import org.deeplearning4j.optimize.api.StepFunction;
import org.deeplearning4j.optimize.api.TerminationCondition;
import org.deeplearning4j.optimize.terminations.EpsTermination;
import org.deeplearning4j.optimize.terminations.ZeroDirection;
import org.nd4j.linalg.api.ndarray.INDArray;
import org.nd4j.linalg.learning.GradientUpdater;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Base optimizer
 * @author Adam Gibson
 */
public abstract class BaseOptimizer implements ConvexOptimizer {

    protected NeuralNetConfiguration conf;
    protected int iteration = 0;
    protected static final Logger log = LoggerFactory.getLogger(BaseOptimizer.class);
    protected StepFunction stepFunction;
    protected Collection<IterationListener> iterationListeners = new ArrayList<>();
    protected Collection<TerminationCondition> terminationConditions = new ArrayList<>();
    protected Model model;
    protected BackTrackLineSearch lineMaximizer;
    protected Updater updater;
    protected double step;
    private int batchSize = 10;
    protected double score,oldScore;
    protected double stepMax = Double.MAX_VALUE;
    public final static String GRADIENT_KEY = "g";
    public final static String SCORE_KEY = "score";
    public final static String PARAMS_KEY = "params";
    public final static String SEARCH_DIR = "searchDirection";
    protected Map<String,Object> searchState = new ConcurrentHashMap<>();

    /**
     *
     * @param conf
     * @param stepFunction
     * @param iterationListeners
     * @param model
     */
    public BaseOptimizer(NeuralNetConfiguration conf,StepFunction stepFunction,Collection<IterationListener> iterationListeners,Model model) {
        this(conf,stepFunction,iterationListeners, Arrays.asList(new ZeroDirection(),new EpsTermination()),model);
    }


    /**
     *
     * @param conf
     * @param stepFunction
     * @param iterationListeners
     * @param terminationConditions
     * @param model
     */
    public BaseOptimizer(NeuralNetConfiguration conf,StepFunction stepFunction,Collection<IterationListener> iterationListeners,Collection<TerminationCondition> terminationConditions,Model model) {
        this.conf = conf;
        this.stepFunction = stepFunction;
        this.iterationListeners = iterationListeners != null ? iterationListeners : new ArrayList<IterationListener>();
        this.terminationConditions = terminationConditions;
        this.model = model;
        lineMaximizer = new BackTrackLineSearch(model,stepFunction,this);
        lineMaximizer.setStepMax(stepMax);
        lineMaximizer.setMaxIterations(conf.getNumLineSearchIterations());

    }


    @Override
    public double score() {
        model.setScore();
        return model.score();
    }


    @Override
    public Pair<Gradient,Double> gradientAndScore() {
        model.setScore();
        Pair<Gradient,Double> pair = model.gradientAndScore();
        for(String paramType : pair.getFirst().gradientForVariable().keySet()) {
            INDArray gradient = pair.getFirst().getGradientFor(paramType);
            updateGradientAccordingToParams(gradient, model, model.batchSize(), paramType,iteration);
        }
        return pair;
    }


    /**
     * Optimize call. This runs the optimizer.
     * @return whether it converged or not
     */
    @Override
    public  boolean optimize() {
        //validate the input before training
        model.validateInput();
        Pair<Gradient,Double> pair = gradientAndScore();
        score = model.score();
        setupSearchState(pair);
        INDArray gradient = (INDArray) searchState.get(GRADIENT_KEY);
        INDArray searchDirection, parameters;

        //pre existing termination conditions
        /*
         * Commented out for now; this has been problematic for testing/debugging
         * Revisit & re-enable later.
        for(TerminationCondition condition : terminationConditions){
            if(condition.terminate(0.0,0.0,new Object[]{gradient})) {
                log.info("Hit termination condition " + condition.getClass().getName());
                return true;
            }
        }*/

        //Preprocess gradient: Calculate search direction, scale gradient etc.
        preProcessLine(gradient);

        for(int i = 0; i < conf.getNumIterations(); i++) {
            //perform one step
            try {
                gradient = (INDArray) searchState.get(GRADIENT_KEY);
                searchDirection = (INDArray) searchState.get(SEARCH_DIR);
                parameters = (INDArray) searchState.get(PARAMS_KEY);
                step = lineMaximizer.optimize(parameters, gradient, searchDirection);
            } catch (InvalidStepException e) {
                log.warn("Invalid step...continuing another iteration: {}",e.getMessage());
            }

            //record old score for deltas and other termination conditions
            oldScore = score;
            pair = gradientAndScore();
            setupSearchState(pair);
            score = pair.getSecond();

            //invoke listeners for debugging
            for(IterationListener listener : iterationListeners)
                listener.iterationDone(model,i);


            //check for termination conditions based on absolute change in score
            for(TerminationCondition condition : terminationConditions){
                if(condition.terminate(score,oldScore,new Object[]{gradient})){
                	log.debug("Hit termination condition: score={}, oldScore={}, condition={}",score,oldScore,condition);
                    return true;
                }
            }

            //post step updates to other search parameters
            postStep();
            this.iteration++;

            //check for termination conditions based on absolute change in score
            for(TerminationCondition condition : terminationConditions)
                if(condition.terminate(score,oldScore,new Object[]{gradient}))
                    return true;


        }

        return true;
    }

    protected  void postFirstStep(INDArray gradient) {
        //no-op
    }

    @Override
    public int batchSize() {
        return batchSize;
    }

    @Override
    public void setBatchSize(int batchSize) {
        this.batchSize = batchSize;
    }


    /**
     * Pre process the line (scaling and the like)
     * @param line the line to pre process
     */
    @Override
    public  void preProcessLine(INDArray line) {
        //no-op
    }
    /**
     * Post step (conjugate gradient among other methods needs this)

     */
    @Override
    public  void postStep() {
        //no-op
    }


    @Override
    public void updateGradientAccordingToParams(INDArray gradient, Model model, int batchSize, String paramType, int iteration) {
        if(updater == null)
            updater = UpdaterCreator.getUpdater(model.conf());
        Layer layer = (Layer) model;
        Gradient g = new DefaultGradient();
        g.setGradientFor(paramType,gradient);
        updater.update(layer,g,iteration);

    }

    /**
     * Setup the initial search state
     * @param pair
     */
    @Override
    public  void setupSearchState(Pair<Gradient, Double> pair) {
        INDArray gradient = pair.getFirst().gradient(conf.variables());
        INDArray params = model.params();
        searchState.put(GRADIENT_KEY,gradient);
        searchState.put(SCORE_KEY,pair.getSecond());
        searchState.put(PARAMS_KEY,params);

    }




}


File: deeplearning4j-core/src/test/java/org/deeplearning4j/optimize/solver/TestOptimizers.java
package org.deeplearning4j.optimize.solver;

import static org.junit.Assert.*;

import java.util.Collection;
import java.util.Map;

import org.deeplearning4j.berkeley.Pair;
import org.deeplearning4j.datasets.iterator.DataSetIterator;
import org.deeplearning4j.datasets.iterator.impl.IrisDataSetIterator;
import org.deeplearning4j.nn.api.Layer;
import org.deeplearning4j.nn.api.Model;
import org.deeplearning4j.nn.api.OptimizationAlgorithm;
import org.deeplearning4j.nn.conf.MultiLayerConfiguration;
import org.deeplearning4j.nn.conf.NeuralNetConfiguration;
import org.deeplearning4j.nn.conf.distribution.NormalDistribution;
import org.deeplearning4j.nn.conf.layers.OutputLayer;
import org.deeplearning4j.nn.conf.layers.RBM;
import org.deeplearning4j.nn.conf.override.ConfOverride;
import org.deeplearning4j.nn.gradient.DefaultGradient;
import org.deeplearning4j.nn.gradient.Gradient;
import org.deeplearning4j.nn.multilayer.MultiLayerNetwork;
import org.deeplearning4j.nn.weights.WeightInit;
import org.deeplearning4j.optimize.api.ConvexOptimizer;
import org.deeplearning4j.optimize.api.IterationListener;
import org.deeplearning4j.optimize.solvers.ConjugateGradient;
import org.deeplearning4j.optimize.solvers.LineGradientDescent;
import org.deeplearning4j.optimize.solvers.StochasticGradientDescent;
import org.deeplearning4j.optimize.solvers.LBFGS;
import org.deeplearning4j.optimize.stepfunctions.DefaultStepFunction;
import org.junit.Test;
import org.nd4j.linalg.api.ndarray.INDArray;
import org.nd4j.linalg.api.rng.DefaultRandom;
import org.nd4j.linalg.api.rng.Random;
import org.nd4j.linalg.factory.Nd4j;
import org.nd4j.linalg.lossfunctions.LossFunctions.LossFunction;

public class TestOptimizers {
	
	@Test
	public void testOptimizersBasicMLPBackprop(){
		//Basic tests of the 'does it throw an exception' variety.
		
		DataSetIterator iter = new IrisDataSetIterator(5,50);
		
		for( OptimizationAlgorithm oa : OptimizationAlgorithm.values() ){
			MultiLayerNetwork network = new MultiLayerNetwork(getMLPConfigIris(oa));
			network.init();
			
			iter.reset();
			network.fit(iter);
		}
	}
	
	private static MultiLayerConfiguration getMLPConfigIris( OptimizationAlgorithm oa ){
		MultiLayerConfiguration c = new NeuralNetConfiguration.Builder()
		.nIn(4).nOut(3)
		.weightInit(WeightInit.DISTRIBUTION)
		.dist(new NormalDistribution(0, 0.1))

		.activationFunction("sigmoid")
		.lossFunction(LossFunction.MCXENT)
		.optimizationAlgo(oa)
		.iterations(1)
		.batchSize(5)
		.constrainGradientToUnitNorm(false)
		.corruptionLevel(0.0)
		.layer(new RBM())
		.learningRate(0.1).useAdaGrad(false)
		.regularization(true)
		.l2(0.01)
		.applySparsity(false).sparsity(0.0)
		.seed(12345L)
		.list(4).hiddenLayerSizes(8,10,5)
		.backward(true).pretrain(false)
		.useDropConnect(false)

		.override(3, new ConfOverride() {
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
	public void testSphereFnOptStochGradDescent(){
		testSphereFnOptHelper(OptimizationAlgorithm.STOCHASTIC_GRADIENT_DESCENT,-1,2);
		testSphereFnOptHelper(OptimizationAlgorithm.STOCHASTIC_GRADIENT_DESCENT,-1,10);
		testSphereFnOptHelper(OptimizationAlgorithm.STOCHASTIC_GRADIENT_DESCENT,-1,100);
	}
	
	@Test
	public void testSphereFnOptLineGradDescent(){
		int[] numLineSearchIter = {1,2,5,10};
		for( int n : numLineSearchIter )
			testSphereFnOptHelper(OptimizationAlgorithm.LINE_GRADIENT_DESCENT,n,2);
		
		for( int n : numLineSearchIter )
			testSphereFnOptHelper(OptimizationAlgorithm.LINE_GRADIENT_DESCENT,n,10);

		for( int n : numLineSearchIter )
			testSphereFnOptHelper(OptimizationAlgorithm.LINE_GRADIENT_DESCENT,n,100);
	}
	
	@Test
	public void testSphereFnOptCG(){
		int[] numLineSearchIter = {1,2,5,10};
		for( int n : numLineSearchIter )
			testSphereFnOptHelper(OptimizationAlgorithm.CONJUGATE_GRADIENT,n,2);
		
		for( int n : numLineSearchIter )
			testSphereFnOptHelper(OptimizationAlgorithm.CONJUGATE_GRADIENT,n,10);
		
		for( int n : numLineSearchIter )
			testSphereFnOptHelper(OptimizationAlgorithm.CONJUGATE_GRADIENT,n,100);
	}
	
	@Test
	public void testSphereFnOptLBFGS(){
		int[] numLineSearchIter = {1,2,5,10};
		for( int n : numLineSearchIter )
			testSphereFnOptHelper(OptimizationAlgorithm.LBFGS,n,2);
		
		for( int n : numLineSearchIter )
			testSphereFnOptHelper(OptimizationAlgorithm.LBFGS,n,10);
		
		for( int n : numLineSearchIter )
			testSphereFnOptHelper(OptimizationAlgorithm.LBFGS,n,100);
	}
	
	//For debugging.
	private static final boolean PRINT_OPT_RESULTS = true;
	public void testSphereFnOptHelper( OptimizationAlgorithm oa, int numLineSearchIter, int nDimensions ){
		
		if( PRINT_OPT_RESULTS ) System.out.println("---------\n Alg=" + oa
				+ ", nIter=" + numLineSearchIter + ", nDimensions=" + nDimensions );
		
		NeuralNetConfiguration conf = new NeuralNetConfiguration.Builder()
		.numLineSearchIterations(numLineSearchIter)
		.iterations(1000)
		.learningRate(0.01)
		.layer(new RBM()).batchSize(1).build();
		conf.addVariable("x");	//Normally done by ParamInitializers, but obviously that isn't done here 
		
		Random rng = new DefaultRandom(12345L);
		org.nd4j.linalg.api.rng.distribution.Distribution dist
			= new org.nd4j.linalg.api.rng.distribution.impl.UniformDistribution(rng,-10, 10);
		Model m = new SphereFunctionModel(nDimensions,dist,conf);
		
		double scoreBefore = m.score();
		assertTrue(!Double.isNaN(scoreBefore) && !Double.isInfinite(scoreBefore));
		if( PRINT_OPT_RESULTS ){
			System.out.println("Before:");
			System.out.println(scoreBefore);
			System.out.println(m.params());
		}
		
		ConvexOptimizer opt;
		switch(oa){
		case STOCHASTIC_GRADIENT_DESCENT:
			opt = new StochasticGradientDescent(conf,new DefaultStepFunction(),null,m);
			break;
		case LINE_GRADIENT_DESCENT:
			opt = new LineGradientDescent(conf,new DefaultStepFunction(),null,m);
			break;
		case CONJUGATE_GRADIENT:
			opt = new ConjugateGradient(conf,new DefaultStepFunction(),null,m);
			break;
		case LBFGS:
			opt = new LBFGS(conf,new DefaultStepFunction(),null,m);
			break;
		default:
			fail("Not supported: " + oa);	//Hessian free is NN-specific.
			opt = null;
			break;
		}
		
		opt.setupSearchState(m.gradientAndScore());
		opt.optimize();
		
		double scoreAfter = m.score();
		assertTrue(!Double.isNaN(scoreAfter) && !Double.isInfinite(scoreAfter));
		if( PRINT_OPT_RESULTS ){
			System.out.println("After:");
			System.out.println(scoreAfter);
			System.out.println(m.params());
		}
		
		//Expected behaviour after optimization:
		//(a) score is better (lower) after optimization.
		//(b) Parameters are closer to minimum after optimization (TODO)
		assertTrue("Score did not improve after optimization (b="+scoreBefore+",a="+scoreAfter+")",scoreAfter < scoreBefore);
		
	}
	
	
	
	
	/** A non-NN optimization problem. Optimization function (cost function) is 
	 * \sum_i x_i^2. Has minimum of 0.0 at x_i=0 for all x_i
	 * See: https://en.wikipedia.org/wiki/Test_functions_for_optimization
	 */
	private static class SphereFunctionModel implements Model, Layer {
		private static final long serialVersionUID = 239156313657395826L;
		private INDArray parameters;
		private final NeuralNetConfiguration conf;
		
		/**@param parameterInit Initial parameters. Also determines dimensionality of problem. Should be row vector.
		 */
		private SphereFunctionModel( INDArray parameterInit, NeuralNetConfiguration conf ){
			this.parameters = parameterInit.dup();
			this.conf = conf;
		}
		
		private SphereFunctionModel( int nParams, org.nd4j.linalg.api.rng.distribution.Distribution distribution,
				NeuralNetConfiguration conf ){
			this.parameters = distribution.sample(new int[]{1,nParams});
			this.conf = conf;
		}

		@Override
		public void fit() { throw new UnsupportedOperationException(); }

		@Override
		public void update(INDArray gradient, String paramType) {
			if(!"x".equals(paramType)) throw new UnsupportedOperationException();
			parameters.subi(gradient);
		}

		@Override
		public double score() {
			return Nd4j.getBlasWrapper().dot(parameters, parameters);	//sum_i x_i^2
		}

		@Override
		public void setScore() { }

		@Override
		public void accumulateScore(double accum) { throw new UnsupportedOperationException(); }

		@Override
		public INDArray transform(INDArray data) { throw new UnsupportedOperationException(); }

		@Override
		public INDArray params() {return parameters; }

		@Override
		public int numParams() { return parameters.length(); }

		@Override
		public void setParams(INDArray params) { this.parameters = params; }

		@Override
		public void fit(INDArray data) { throw new UnsupportedOperationException(); }

		@Override
		public void iterate(INDArray input) { throw new UnsupportedOperationException(); }

		@Override
		public Gradient gradient() {
			// Gradients: d(x^2)/dx = 2x
			INDArray gradient = parameters.mul(2);
			Gradient g = new DefaultGradient();
			g.gradientForVariable().put("x", gradient);
			return g;
		}

		@Override
		public Pair<Gradient, Double> gradientAndScore() {
			return new Pair<Gradient,Double>(gradient(),score());
		}

		@Override
		public int batchSize() { return 1; }

		@Override
		public NeuralNetConfiguration conf() { return conf; }

		@Override
		public void setConf(NeuralNetConfiguration conf) { throw new UnsupportedOperationException(); }

		@Override
		public INDArray input() {
			//Work-around for BaseUpdater.postApply(): Uses Layer.input().size(0)
			//in order to get mini-batch size. i.e., divide by 1 here.
			return Nd4j.zeros(1);
		}

		@Override
		public void validateInput() { }

		@Override
		public ConvexOptimizer getOptimizer() { throw new UnsupportedOperationException(); }

		@Override
		public INDArray getParam(String param) { return parameters; }

		@Override
		public void initParams() { throw new UnsupportedOperationException(); }

		@Override
		public Map<String, INDArray> paramTable() { throw new UnsupportedOperationException(); }

		@Override
		public void setParamTable(Map<String, INDArray> paramTable) { throw new UnsupportedOperationException(); }

		@Override
		public void setParam(String key, INDArray val) { throw new UnsupportedOperationException(); }

		@Override
		public void clear() { throw new UnsupportedOperationException(); }

		@Override
		public Type type() { throw new UnsupportedOperationException(); }

		@Override
		public Gradient error(INDArray input) { throw new UnsupportedOperationException(); }

		@Override
		public INDArray derivativeActivation(INDArray input) { throw new UnsupportedOperationException(); }

		@Override
		public Gradient calcGradient(Gradient layerError, INDArray indArray) { throw new UnsupportedOperationException(); }

		@Override
		public Gradient errorSignal(Gradient error, INDArray input){ throw new UnsupportedOperationException(); }

		@Override
		public Gradient backwardGradient(INDArray z, Layer nextLayer,
				Gradient nextGradient, INDArray activation) { throw new UnsupportedOperationException(); }

		@Override
		public void merge(Layer layer, int batchSize) { throw new UnsupportedOperationException(); }

		@Override
		public INDArray activationMean() { throw new UnsupportedOperationException(); }

		@Override
		public INDArray preOutput(INDArray x) { throw new UnsupportedOperationException(); }

		@Override
		public INDArray activate() { throw new UnsupportedOperationException(); }

		@Override
		public INDArray activate(INDArray input) { throw new UnsupportedOperationException(); }

		@Override
		public Layer transpose() { throw new UnsupportedOperationException(); }

		@Override
		public Layer clone() { throw new UnsupportedOperationException(); }

		@Override
		public Pair<Gradient, Gradient> backWard(Gradient errors,
				Gradient deltas, INDArray activation, String previousActivation) { throw new UnsupportedOperationException(); }

		@Override
		public Collection<IterationListener> getIterationListeners() { return null; }

		@Override
		public void setIterationListeners(Collection<IterationListener> listeners) { throw new UnsupportedOperationException(); }

		@Override
		public void setIndex(int index) { throw new UnsupportedOperationException(); }

		@Override
		public int getIndex() { throw new UnsupportedOperationException(); }
	}
}
